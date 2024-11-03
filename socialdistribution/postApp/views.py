# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets, permissions
from .serializers import PostSerializer, CommentSerializer, LikeSerializer
from rest_framework.permissions import IsAuthenticated


# Third-party imports
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Project imports
from authorApp.models import AuthorProfile, Friends
from node_link.models import Notification
from node_link.utils.common import has_access
from postApp.models import Comment, Like, Post

# Package imports
import commonmark


@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title", "New Post")
        content = request.POST.get("content", "")
        # img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility", "p")
        is_commonmark = request.POST.get("is_commonmark") == "true"
        author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
        content_type = ""
        if is_commonmark:
            content_type = "c"

        # Create the post with the necessary fields
        Post.objects.create(
            title=title,
            content=content,
            visibility=visibility,
            contentType=content_type,
            author=author,
            node=author.local_node,  # Associate the post with the author's node
            created_by=author,
            updated_by=author,
        )
        # Redirect to the post list page SEdBo49hPQ4
        return redirect("node_link:home")

    return render(request, "create_post.html")


@login_required
def create_comment(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)

    if request.method == "POST":
        content = request.POST.get("content")

        author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

        # Create the comment
        Comment.objects.create(
            content=content,
            visibility="p",
            post=post,
            author=author,
            created_by=author,
            updated_by=author,
        )
        # Redirect back to the post detail page
        return render(request, "create_comment_card.html", {"success": True})

    return render(request, "create_comment_card.html", {"post": post})


@login_required
def like_post(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)
    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

    existing_like = Like.objects.filter(post=post, author=author)
    if existing_like.exists():
        existing_like.delete()
        # Delete the corresponding notification
        Notification.objects.filter(
            user=post.author,
            notification_type="like",
            related_object_id=str(post.id),
            message=f"{author.user.username} liked your post.",
        ).delete()
    else:
        Like.objects.create(
            post=post,
            author=author,  # Include the author field
            created_by=author,
            updated_by=author,
        )

    return redirect("postApp:post_detail", post_uuid)


@login_required
def delete_post(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)
    # check if they are allow to delete
    if post.author.user == request.user:
        post.visibility = "d"
        post.save()
    return redirect("node_link:home")


# view post


@login_required
def post_card(
    request, post_uuid: str
):  #!!!POST NOTE: Must be updated with new content handling
    """renders a single card

    Args:
        request (_type_): _description_
        id (_type_): _description_

    Returns:
        _type_: _description_
    """
    post = get_object_or_404(Post, uuid=post_uuid)
    # check is user has permission to see post
    if has_access(request=request, post_uuid=post_uuid):

        user_has_liked = post.postliked.filter(
            author=request.user.author_profile
        ).exists()
        user_img = post.author.user.profileImage

        if post.contentType == "c":
            # Convert Markdown to HTML
            parser = commonmark.Parser()
            renderer = commonmark.HtmlRenderer()
            post_content = renderer.render(parser.parse(post.content))
        else:
            post_content = post.content

        context = {
            "post": post,
            "post_content": post_content,
            "user_has_liked": user_has_liked,
            "profileImg": user_img,
        }
        return render(request, "post_card.html", context)
    return HttpResponseForbidden("You are not supposed to be here. Go Home!")


@login_required
def post_detail(request, post_uuid: str):
    post = get_object_or_404(Post, uuid=post_uuid)
    if has_access(request=request, post_uuid=post_uuid):
        user_has_liked = False

        if request.user.is_authenticated:
            try:
                author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
                user_has_liked = post.postliked.filter(author=author).exists()
            except AuthorProfile.DoesNotExist:
                # Handle the case where the Author profile does not exist
                messages.error(request, "Author profile not found.")
                # Optionally, redirect or set user_has_liked to False
                redirect("post_list")

        user_has_liked = post.postliked.filter(author=author.id).exists()
        comment_list = list(post.comments.filter().order_by("-created_at"))

        return render(
            request,
            "post_details.html",
            {
                "post": post,
                "user_has_liked": user_has_liked,
                "a_username": post.author,
                "comment_list": comment_list,
            },
        )
    else:
        return HttpResponseForbidden("You are not supposed to be here. Go Home!")


class PostViewSet(viewsets.ModelViewSet):
    """API endpoint for managing posts"""

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        author_serial = self.kwargs.get("author_serial")
        if author_serial:
            return Post.objects.filter(author__user__username=author_serial).order_by(
                "-created_at"
            )
        return Post.objects.all()

    @swagger_auto_schema(
        operation_description="Retrieve a list of posts for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author whose posts are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for pagination.",
                type=openapi.TYPE_INTEGER,
                required=False,
                example=1,
            ),
            openapi.Parameter(
                "size",
                openapi.IN_QUERY,
                description="Number of posts per page.",
                type=openapi.TYPE_INTEGER,
                required=False,
                example=10,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of posts retrieved successfully.",
                schema=PostSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "uuid": "post1-uuid",
                            "title": "First Post",
                            "content": "This is the content of the first post.",
                            "author": {
                                "id": "author1-id",
                                "username": "johndoe",
                            },
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new post for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author creating the post.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
        request_body=PostSerializer,
        responses={
            201: openapi.Response(
                description="Post created successfully.",
                schema=PostSerializer(),
                examples={
                    "application/json": {
                        "uuid": "new-post-uuid",
                        "title": "New Post",
                        "content": "Content of the new post.",
                        "author": {
                            "id": "author1-id",
                            "username": "johndoe",
                        },
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You cannot create posts for another author.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def create(self, request, *args, **kwargs):
        author_serial = self.kwargs.get("author_serial")
        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        if request.user.author_profile != author:
            raise PermissionDenied("You cannot create posts for another author.")
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific post by UUID for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the post to retrieve.",
                type=openapi.TYPE_STRING,
                required=True,
                example="post1-uuid",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Post retrieved successfully.",
                schema=PostSerializer(),
                examples={
                    "application/json": {
                        "uuid": "post1-uuid",
                        "title": "First Post",
                        "content": "This is the content of the first post.",
                        "author": {
                            "id": "author1-id",
                            "username": "johndoe",
                        },
                    }
                },
            ),
            404: "Not Found - Post does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a post entirely for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the post to update.",
                type=openapi.TYPE_STRING,
                required=True,
                example="post1-uuid",
            ),
        ],
        request_body=PostSerializer,
        responses={
            200: openapi.Response(
                description="Post updated successfully.",
                schema=PostSerializer(),
                examples={
                    "application/json": {
                        "uuid": "post1-uuid",
                        "title": "Updated Post Title",
                        "content": "Updated content.",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You do not have permission to edit this post.",
            404: "Not Found - Post does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a post for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the post to partially update.",
                type=openapi.TYPE_STRING,
                required=True,
                example="post1-uuid",
            ),
        ],
        request_body=PostSerializer,
        responses={
            200: openapi.Response(
                description="Post partially updated successfully.",
                schema=PostSerializer(),
                examples={
                    "application/json": {
                        "uuid": "post1-uuid",
                        "title": "Partially Updated Post Title",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You do not have permission to edit this post.",
            404: "Not Found - Post does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a post for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the post to delete.",
                type=openapi.TYPE_STRING,
                required=True,
                example="post1-uuid",
            ),
        ],
        responses={
            204: "No Content - Post deleted successfully.",
            403: "Forbidden - You do not have permission to delete this post.",
            404: "Not Found - Post does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CommentViewSet(viewsets.ModelViewSet):
    """API endpoint for managing comments"""

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        author_serial = self.kwargs.get("author_serial")
        if author_serial:
            return Comment.objects.filter(author__user__username=author_serial)
        return Comment.objects.all()

    @swagger_auto_schema(
        operation_description="Retrieve a list of comments for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author whose comments are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for pagination.",
                type=openapi.TYPE_INTEGER,
                required=False,
                example=1,
            ),
            openapi.Parameter(
                "size",
                openapi.IN_QUERY,
                description="Number of comments per page.",
                type=openapi.TYPE_INTEGER,
                required=False,
                example=10,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of comments retrieved successfully.",
                schema=CommentSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "uuid": "comment1-uuid",
                            "content": "This is a comment.",
                            "author": {
                                "id": "author1-id",
                                "username": "johndoe",
                            },
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Comments"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new comment for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author creating the comment.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
        request_body=CommentSerializer,
        responses={
            201: openapi.Response(
                description="Comment created successfully.",
                schema=CommentSerializer(),
                examples={
                    "application/json": {
                        "uuid": "new-comment-uuid",
                        "content": "This is a new comment.",
                        "author": {
                            "id": "author1-id",
                            "username": "johndoe",
                        },
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You cannot create comments for another author.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Comments"],
    )
    def create(self, request, *args, **kwargs):
        author_serial = self.kwargs.get("author_serial")
        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        if request.user.author_profile != author:
            raise PermissionDenied("You cannot create comments for another author.")
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific comment by UUID for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the comment to retrieve.",
                type=openapi.TYPE_STRING,
                required=True,
                example="comment1-uuid",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Comment retrieved successfully.",
                schema=CommentSerializer(),
                examples={
                    "application/json": {
                        "uuid": "comment1-uuid",
                        "content": "This is a comment.",
                        "author": {
                            "id": "author1-id",
                            "username": "johndoe",
                        },
                    }
                },
            ),
            404: "Not Found - Comment does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Comments"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a comment entirely for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the comment to update.",
                type=openapi.TYPE_STRING,
                required=True,
                example="comment1-uuid",
            ),
        ],
        request_body=CommentSerializer,
        responses={
            200: openapi.Response(
                description="Comment updated successfully.",
                schema=CommentSerializer(),
                examples={
                    "application/json": {
                        "uuid": "comment1-uuid",
                        "content": "Updated comment content.",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You do not have permission to edit this comment.",
            404: "Not Found - Comment does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Comments"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a comment for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the comment to partially update.",
                type=openapi.TYPE_STRING,
                required=True,
                example="comment1-uuid",
            ),
        ],
        request_body=CommentSerializer,
        responses={
            200: openapi.Response(
                description="Comment partially updated successfully.",
                schema=CommentSerializer(),
                examples={
                    "application/json": {
                        "uuid": "comment1-uuid",
                        "content": "Partially updated content.",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You do not have permission to edit this comment.",
            404: "Not Found - Comment does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Comments"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a comment for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the comment to delete.",
                type=openapi.TYPE_STRING,
                required=True,
                example="comment1-uuid",
            ),
        ],
        responses={
            204: "No Content - Comment deleted successfully.",
            403: "Forbidden - You do not have permission to delete this comment.",
            404: "Not Found - Comment does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Comments"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class LikeViewSet(viewsets.ModelViewSet):
    """API endpoint for managing likes"""

    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        author_serial = self.kwargs.get("author_serial")
        if author_serial:
            return Like.objects.filter(author__user__username=author_serial)
        return Like.objects.all()

    @swagger_auto_schema(
        operation_description="Retrieve a list of likes for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author whose likes are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for pagination.",
                type=openapi.TYPE_INTEGER,
                required=False,
                example=1,
            ),
            openapi.Parameter(
                "size",
                openapi.IN_QUERY,
                description="Number of likes per page.",
                type=openapi.TYPE_INTEGER,
                required=False,
                example=10,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of likes retrieved successfully.",
                schema=LikeSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "uuid": "like1-uuid",
                            "post": "post1-uuid",
                            "author": {
                                "id": "author1-id",
                                "username": "johndoe",
                            },
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Likes"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new like for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author creating the like.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
        request_body=LikeSerializer,
        responses={
            201: openapi.Response(
                description="Like created successfully.",
                schema=LikeSerializer(),
                examples={
                    "application/json": {
                        "uuid": "new-like-uuid",
                        "post": "post1-uuid",
                        "author": {
                            "id": "author1-id",
                            "username": "johndoe",
                        },
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You cannot create likes for another author.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Likes"],
    )
    def create(self, request, *args, **kwargs):
        author_serial = self.kwargs.get("author_serial")
        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        if request.user.author_profile != author:
            raise PermissionDenied("You cannot create likes for another author.")
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific like by UUID for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the like to retrieve.",
                type=openapi.TYPE_STRING,
                required=True,
                example="like1-uuid",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Like retrieved successfully.",
                schema=LikeSerializer(),
                examples={
                    "application/json": {
                        "uuid": "like1-uuid",
                        "post": "post1-uuid",
                        "author": {
                            "id": "author1-id",
                            "username": "johndoe",
                        },
                    }
                },
            ),
            404: "Not Found - Like does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Likes"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a like entirely for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the like to update.",
                type=openapi.TYPE_STRING,
                required=True,
                example="like1-uuid",
            ),
        ],
        request_body=LikeSerializer,
        responses={
            200: openapi.Response(
                description="Like updated successfully.",
                schema=LikeSerializer(),
                examples={
                    "application/json": {
                        "uuid": "like1-uuid",
                        "post": "post1-uuid",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You do not have permission to edit this like.",
            404: "Not Found - Like does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Likes"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a like for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the like to partially update.",
                type=openapi.TYPE_STRING,
                required=True,
                example="like1-uuid",
            ),
        ],
        request_body=LikeSerializer,
        responses={
            200: openapi.Response(
                description="Like partially updated successfully.",
                schema=LikeSerializer(),
                examples={
                    "application/json": {
                        "uuid": "like1-uuid",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            403: "Forbidden - You do not have permission to edit this like.",
            404: "Not Found - Like does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Likes"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a like for a specific author.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="UUID of the like to delete.",
                type=openapi.TYPE_STRING,
                required=True,
                example="like1-uuid",
            ),
        ],
        responses={
            204: "No Content - Like deleted successfully.",
            403: "Forbidden - You do not have permission to delete this like.",
            404: "Not Found - Like does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Likes"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
