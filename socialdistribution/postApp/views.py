# Django imports
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    JsonResponse,
    HttpResponse,
    Http404,
)
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets
from .serializers import PostSerializer, CommentSerializer, LikeSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied


# Third-party imports
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Project imports
from authorApp.models import AuthorProfile
from node_link.models import Notification
from node_link.utils.common import has_access, is_approved
from postApp.models import Comment, Like, Post
from postApp.utils.image_check import check_image

# Package imports
import commonmark
import base64
from datetime import datetime
from PIL import Image
import re


@is_approved
def create_post(request, username):
    return render(request, "create_post.html")


@is_approved
def submit_post(request, username):
    if request.method == "POST":
        title = request.POST.get("title", "New Post")
        description = request.POST.get("description", "")
        content = request.POST.get("content", "")
        visibility = request.POST.get("visibility", "p")
        content_type = request.POST.get("contentType", "p")
        author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
        print(f"contentt type: {content_type}")
        # Handle image upload
        if content_type in ["png", "jpeg", "a"]:
            img = request.FILES.get("img", None)
            if img:
                try:
                    content, _ = check_image(img, content_type, True)
                except (IOError, SyntaxError):
                    # The file is not a valid image
                    return redirect(
                        "postApp:create_post", username=username
                    )  # Early exit
            else:
                # If no image is uploaded but content_type expects one
                raise ValidationError("Image file is required for image posts.")

        # Create the post with the necessary fields
        Post.objects.create(
            title=title,
            description=description,
            content=content,
            visibility=visibility,
            contentType=content_type,
            author=author,
            node=author.local_node,  # Associate the post with the author's node
            created_by=author,
            updated_by=author,
        )
        # Redirect to the post list page
        return redirect("node_link:home", username=username)
    return redirect("node_link:home", username=username)


@is_approved
def create_comment(request, username, post_uuid):
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


@is_approved
def like_post(request, username, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)
    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

    Like.objects.create(
        post=post,
        author=author,  # Include the author field
        created_by=author,
        updated_by=author,
    )

    return redirect("postApp:post_detail", username, post_uuid)


@is_approved
def delete_post(request, username, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)
    # check if they are allow to delete
    if post.author.user == request.user:
        post.visibility = "d"
        post.save()
    return redirect("node_link:home", username=username)


@is_approved
def edit_post(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)

    if post.author.user != request.user:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    # Determine active tab based on contentType
    if post.contentType == "p":
        active_tab = "PlainText"
    elif post.contentType == "m":
        active_tab = "Markdown"
    elif post.contentType in ["png", "jpeg", "a"]:
        active_tab = "Image"
    else:
        active_tab = "PlainText"  # Default to PlainText if unknown

    # Define image types for conditional rendering
    image_types = ["png", "jpeg"]

    # Handle GET request to render the form with pre-filled data
    if request.method == "GET":
        context = {
            "post": post,
            "active_tab": active_tab,
            "image_types": image_types,
        }
        return render(request, "edit_post.html", context)
    else:
        # If request method is not GET, redirect to edit page
        return redirect("postApp:edit_post", post_uuid=post_uuid)


@is_approved
def submit_edit_post(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)

    if post.author.user != request.user:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if request.method != "POST":
        return redirect(
            "postApp:edit_post", post_uuid=post_uuid
        )  # Early exit if not POST

    # Extract form data with defaults
    title = request.POST.get("title", post.title)
    description = request.POST.get("description", post.description)
    content = request.POST.get("content", post.content)
    visibility = request.POST.get("visibility", post.visibility)
    content_type = request.POST.get("contentType", post.contentType)
    submit_type = request.POST.get("submit_type", "plain")  # From updated form

    # Handle image upload if content type is image
    if submit_type == "image":
        img = request.FILES.get("img", None)
        if img:
            # Server-Side Validation: Check file size (e.g., max 2MB)
            MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2 MB
            if img.size > MAX_UPLOAD_SIZE:
                messages.error(request, "Image file too large ( > 2MB ).")
                return redirect("postApp:edit_post", post_uuid=post_uuid)  # Early exit

            try:
                content, actual_content_type = check_image(img, content_type, False)
                content_type = actual_content_type

            except (IOError, SyntaxError):
                # The file is not a valid image
                return redirect("postApp:edit_post", post_uuid=post_uuid)  # Early exit
        else:
            # If no new image is uploaded, keep the existing content
            content = post.content
            # Optionally, you might want to reset content_type if the previous post was an image
            # Or keep it as is to preserve the original type

    # Update the post with new data
    post.title = title
    post.description = description
    post.content = content
    post.visibility = visibility
    post.contentType = content_type
    post.updated_by = request.user.author_profile
    post.updated_at = datetime.now()
    post.save()

    return redirect(
        "postApp:post_detail", username=request.user.username, post_uuid=post_uuid
    )


# view post


@is_approved
def post_card(
    request, username, post_uuid: str
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

        if post.contentType == "m":
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


@is_approved
def post_detail(request, username, post_uuid: str):
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


# renders the form for sharing the post to other authors
@is_approved
def render_share_form(request, author_serial, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid, author__user__username=author_serial)

    if post.visibility != "p":
        return HttpResponseForbidden("You can only share public posts.")

    authors = AuthorProfile.objects.exclude(user=request.user)
    context = {
        "post": post,
        "authors": authors,
    }
    return render(request, "share_post_form.html", context)


@is_approved
def handle_share_post(request, author_serial, post_uuid):
    # POST Request
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    post = get_object_or_404(Post, uuid=post_uuid, author__user__username=author_serial)

    # ensure that the post is actually public
    if post.visibility != "p":
        return HttpResponseForbidden("You can only share public posts.")

    recipient_ids = request.POST.getlist("recipients")
    recipients = AuthorProfile.objects.filter(id__in=recipient_ids).exclude(
        user=request.user
    )

    for recipient in recipients:
        message = f"{request.user.username} shared a post with you."
        link_url = reverse(
            "postApp:post_detail", args=[post.author.user.username, post.uuid]
        )
        Notification.objects.create(
            user=recipient,
            message=message,
            notification_type="shared_post",
            related_object_id=str(post.id),
            author_picture_url=request.user.author_profile.user.profileImage,
            link_url=link_url,
        )

        # Response to close the modal
        return JsonResponse({"success": True})


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

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user.author_profile,
            node=self.request.user.author_profile.local_node,
            created_by=self.request.user.author_profile,
            updated_by=self.request.user.author_profile,
        )


class LocalPostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(
            visibility__in=["p", "u"], uuid=self.kwargs.get("uuid")
        )


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


class PostImageView(APIView):
    def get(self, request, author_serial, post_uuid):
        # Step 1: Retrieve the post
        post = get_object_or_404(
            Post, uuid=post_uuid, author__user__username=author_serial
        )

        # Step 2: Check if the post is public
        if post.visibility != "p":
            return Response(
                {"detail": "Post is not public."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Step 3: Determine the content type based on your conditionals
        content_type_main = None
        if post.contentType == "jpeg":
            content_type_main = "image/jpeg"
        elif post.contentType == "png":
            content_type_main = "image/png"
        else:
            content_type_main = "application/base64"

        # Step 4: Validate that the contentType is an image
        if content_type_main not in ["image/png", "image/jpeg", "application/base64"]:
            raise Http404("Post content is not an image.")

        # Step 5: Extract base64 data from content
        content = post.content.strip()

        if content.startswith("data:"):
            # Extract the base64 data from data URI
            match = re.match(
                r"data:(?P<mime_type>.+);base64,(?P<base64_data>.+)", content
            )
            if not match:
                raise Http404("Invalid image data.")
            base64_data = match.group("base64_data")
            mime_type = match.group("mime_type")
        else:
            # Content is raw base64 data without data URI
            base64_data = content
            mime_type = content_type_main  # Use the main content type

        # Remove any whitespace or newlines that may corrupt base64 decoding
        base64_data = base64_data.replace("\n", "").replace("\r", "")

        try:
            image_data = base64.b64decode(base64_data)
        except (TypeError, ValueError) as exc:
            raise Http404("Invalid image data.") from exc

        # Step 6: Detect the image type from binary data if necessary
        if post.contentType == "a" or mime_type in ("application/base64", None):
            # Detect image type from binary data
            image_type = self.detect_image_type(image_data)
            if not image_type:
                raise Http404("Unsupported or invalid image format.")
            mime_type = image_type
            print(f"Detected Image Type: {mime_type}")

        # Step 7: Set the correct content type
        content_type = mime_type  # Use the extracted or determined MIME type

        # Step 8: Return the image data with correct headers
        response = HttpResponse(image_data, content_type=content_type)
        response["Content-Length"] = len(image_data)
        return response

    def detect_image_type(self, image_data):
        # Read the first few bytes to detect the image type
        header = image_data[:12]  # Read more bytes to accommodate longer signatures

        content_type = ""
        # JPEG
        if header.startswith(b"\xFF\xD8\xFF"):
            content_type = "image/jpeg"

        # PNG (including APNG)
        elif header.startswith(b"\x89PNG\r\n\x1A\n"):
            # For APNG detection, more in-depth analysis is needed
            content_type = "image/png"

        # GIF
        elif header[:6] in (b"GIF87a", b"GIF89a"):
            content_type = "image/gif"

        # WebP
        elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            content_type = "image/webp"

        # AVIF
        elif header[4:12] == b"ftypavif":
            content_type = "image/avif"

        # SVG
        elif header.strip().startswith(b"<?xml") or b"<svg" in header.lower():
            content_type = "image/svg+xml"

        else:
            content_type = None  # Unsupported image type

        return content_type
