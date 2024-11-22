# Django imports
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
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
from .serializers import (
    PostSerializer,
    CommentSerializer,
    LikeSerializer,
    CommentsSerializer,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied


# Third-party imports
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Project imports
from authorApp.models import AuthorProfile, User, Follower
from node_link.models import Notification
from node_link.utils.common import has_access, is_approved
from node_link.utils.communication import send_to_remote_inboxes

from postApp.models import Comment, Like, Post
from postApp.utils.image_check import check_image
from authorApp.serializers import AuthorProfileSerializer
from postApp.serializers import CommentSerializer

# Package imports
import commonmark
import base64
from datetime import datetime
from PIL import Image
import re
from urllib.parse import unquote, urljoin
import uuid
import requests


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
        post = Post.objects.create(
            title=title,
            description=description,
            content=content,
            visibility=visibility,
            contentType=content_type,
            author=author,
            node=author.user.local_node,  # Associate the post with the author's node
            created_by=author,
            updated_by=author,
        )

        post.post_serial = post.uuid
        post.save()

        post_json = PostSerializer(post, context={"request": request}).data

        remote_followers = Follower.objects.filter(
            object=author, actor__user__local_node__is_remote=True
        ).values_list("actor__id", flat=True)

        for a in AuthorProfile.objects.filter(id__in=remote_followers):

            send_to_remote_inboxes(post_json, a)

        # Redirect to the post list page
        return redirect("node_link:home", username=username)
    return redirect("node_link:home", username=username)


def send_post_to_remote_inboxes(post_json):
    """
    Send the post JSON object to the inbox of all remote users.

    Args:
        post_json (dict): The post JSON object to send.
    """
    # Find all remote users (usernames containing '__')
    remote_users = User.objects.filter(username__contains="__")

    for user in remote_users:
        # Extract the remote node's URL and credentials
        try:
            node = user.local_node  # Assume `local_node` points to the Node model
        except AttributeError:
            print(f"User {user.username} does not have an associated node.")
            continue

        if not node.url or not node.username or not node.password:
            print(f"Node for user {user.username} is missing credentials or URL.")
            continue

        # Extract the remote author's username
        remote_author_serial = user.username.split("__")[1]

        # Construct the inbox URL
        inbox_url = f"{node.url.rstrip('/')}/api/authors/{remote_author_serial}/inbox/"

        # Send the POST request to the inbox
        try:
            response = requests.post(
                inbox_url,
                json=post_json,
                auth=(node.username, "testing"),
                timeout=10,
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            print(
                f"Successfully sent post to {inbox_url}. Response: {response.status_code}"
            )
        except requests.exceptions.RequestException as e:
            print(f"Failed to send post to {inbox_url}. Error: {str(e)}")


@is_approved
def create_comment(request, username, post_uuid):

    post = get_object_or_404(Post, uuid=post_uuid)

    if request.method == "POST":
        content = request.POST.get("content")

        author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

        # Create the comment
        comment = Comment.objects.create(
            content=content,
            visibility="p",
            post=post,
            author=author,
            created_by=author,
            updated_by=author,
        )
        # Redirect back to the post detail page

        comment.comment_serial = comment.uuid
        comment.save()

        return render(request, "create_comment_card.html", {"success": True})

    return render(request, "create_comment_card.html", {"post": post})


@is_approved
def like_post(request, username, post_uuid):

    post = get_object_or_404(Post, uuid=post_uuid)

    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

    like = Like.objects.create(
        post=post,
        author=author,  # Include the author field
        created_by=author,
        updated_by=author,
    )

    like.like_serial = like.uuid
    like.save()

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
def edit_post(request, username, post_uuid):

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
        return redirect("postApp:edit_post", username=username, post_uuid=post_uuid)


@is_approved
def submit_edit_post(request, username, post_uuid):

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
                return redirect(
                    "postApp:edit_post", username=username, post_uuid=post_uuid
                )  # Early exit

            try:
                content, actual_content_type = check_image(img, content_type, False)
                content_type = actual_content_type

            except (IOError, SyntaxError):
                # The file is not a valid image
                return redirect(
                    "postApp:edit_post", username=username, post_uuid=post_uuid
                )  # Early exit
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
    if has_access(request=request, post_uuid=post_uuid, username=username):

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
    if has_access(request=request, post_uuid=post_uuid, username=username):
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
                examples={
                    "application/json": {
                        "type": "posts",
                        "page_number": 1,
                        "size": 10,
                        "count": 42,
                        "src": [
                            {
                                "id": "http://nodeaaaa/api/authors/johndoe/posts/1",
                                "type": "post",
                                "title": "My First Post",
                                "description": "A short description",
                                "content": "Hello world!",
                                "visibility": "PUBLIC",
                                "author": {
                                    "id": "http://nodeaaaa/api/authors/johndoe",
                                    "host": "http://nodeaaaa/api/",
                                    "type": "author",
                                    "displayName": "John Doe",
                                    "github": "http://github.com/johndoe",
                                    "profileImage": "http://nodeaaaa/api/authors/johndoe/image",
                                    "page": "http://nodeaaaa/authors/johndoe",
                                },
                                "contentType": "text/plain",
                                "published": "2024-11-17T12:00:00+00:00",
                            },
                            # More post objects
                        ],
                    }
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Posts"],
    )
    def list(self, request, *args, **kwargs):
        """
        Custom list method to return paginated posts in the required format.
        """
        # Get queryset
        queryset = self.filter_queryset(self.get_queryset())

        # Paginate the queryset
        paginator = PageNumberPagination()
        paginator.page_size = int(
            request.query_params.get("size", 10)
        )  # Default page size: 10
        page = paginator.paginate_queryset(queryset, request)

        # Serialize the data
        serializer = self.get_serializer(page, many=True)

        # Construct the response format
        response_data = {
            "type": "posts",
            "page_number": paginator.page.number,
            "size": paginator.page_size,
            "count": paginator.page.paginator.count,
            "src": serializer.data,
        }

        return Response(response_data)

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
                            "display_name": "John Doe",
                            "profile_image": "http://example.com/images/johndoe.png",
                            "github": "https://github.com/johndoe",
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
                            "display_name": "John Doe",
                            "profile_image": "http://example.com/images/johndoe.png",
                            "github": "https://github.com/johndoe",
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
            node=self.request.user.local_node,
            created_by=self.request.user.author_profile,
            updated_by=self.request.user.author_profile,
        )


class LocalPostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Retrieve a list of local posts",
        operation_description=(
            "Retrieve a list of posts that are either public or unlisted and match the provided UUID."
        ),
        responses={
            200: openapi.Response(
                description="A list of posts.",
                schema=PostSerializer(many=True),
            ),
            403: openapi.Response(description="Unauthorized access."),
        },
        tags=["Posts"],
    )
    def get_queryset(self):
        return Post.objects.filter(
            visibility__in=["p", "u"], uuid=self.kwargs.get("uuid")
        )


class PostImageView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve an image for a specific post",
        operation_description=(
            "Fetch the image content of a specific post. The image can be in JPEG, PNG, "
            "or Base64 format, based on the content type of the post."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author who created the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "post_uuid",
                openapi.IN_PATH,
                description="UUID of the post whose image is to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="Image data returned successfully."),
            403: openapi.Response(description="Post is not public."),
            404: openapi.Response(description="Post not found or image invalid."),
        },
        tags=["Posts", "Images"],
    )
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


class CommentedView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve comments by author or comment ID",
        operation_description=(
            "Fetch a specific comment by its ID or list all comments by an author. "
            "Supports pagination for comments listing."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author whose comments are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "comment_serial",
                openapi.IN_PATH,
                description="UUID of the specific comment to retrieve.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated comment results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of comments or details of a specific comment.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comments"
                        ),
                        "page": openapi.Schema(type=openapi.TYPE_STRING),
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "page_number": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="comment"
                                    ),
                                    "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                                    "content": openapi.Schema(type=openapi.TYPE_STRING),
                                    "contentType": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="text/markdown",
                                    ),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "id": openapi.Schema(type=openapi.TYPE_STRING),
                                    "post": openapi.Schema(type=openapi.TYPE_STRING),
                                    "page": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(description="Comment or author not found."),
            400: openapi.Response(description="Invalid request."),
        },
        tags=["Comments"],
    )
    def get(self, request, author_serial=None, comment_serial=None):
        """
        GET: Fetch comments by an author or a specific comment
        """
        if author_serial and comment_serial:
            # Retrieve a specific comment
            comment = get_object_or_404(
                Comment, uuid=comment_serial, author__user__username=author_serial
            )
            serializer = CommentSerializer(comment, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif author_serial:
            # List all comments by the author
            author = get_object_or_404(AuthorProfile, user__username=author_serial)
            comments = Comment.objects.filter(author=author)
            if request.get_host() != author.user.local_node.url:
                comments = comments.filter(post__visibility__in=["p", "u"])

            # Pagination logic (~5 comments per page)
            page_size = 5
            page_number = int(request.query_params.get("page", 1))
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size

            paginated_comments = comments[start_index:end_index]

            # Total comment count
            total_count = comments.count()

            # Construct response metadata
            base_url = (
                request.build_absolute_uri("/") if request else "http://localhost/"
            )
            author_page = urljoin(base_url, f"authors/{author.user.username}")
            api_page = urljoin(base_url, f"api/authors/{author.user.username}/comments")

            # Prepare response data
            response_data = {
                "type": "comments",
                "page": author_page,
                "id": api_page,
                "page_number": page_number,
                "size": page_size,
                "count": total_count,
                "src": paginated_comments,  # Pass the queryset directly
            }

            # Serialize and return the response
            serializer = CommentsSerializer(response_data, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_summary="Add a new comment",
        operation_description="Create a new comment on a specified post by providing the author's username and the post's URL.",
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author creating the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["type", "post", "comment"],
            properties={
                "type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="comment",
                    description="Type of the object. Must be 'comment'.",
                ),
                "post": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="http://localhost/api/authors/author123/posts/post-uuid",
                    description="Full URL of the post being commented on.",
                ),
                "comment": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="This is a sample comment.",
                    description="The content of the comment.",
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Comment created successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comment"
                        ),
                        "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "content": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="This is a sample comment.",
                        ),
                        "contentType": openapi.Schema(
                            type=openapi.TYPE_STRING, example="text/markdown"
                        ),
                        "published": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "post": openapi.Schema(type=openapi.TYPE_STRING),
                        "page": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Invalid input. Includes missing or incorrect fields.",
                examples={
                    "application/json": {"detail": "Invalid comment type."},
                },
            ),
            404: openapi.Response(
                description="Author or post not found.",
                examples={
                    "application/json": {"detail": "Invalid post URL or UUID."},
                },
            ),
        },
        tags=["Comments"],
    )
    def post(self, request, author_serial=None):
        """
        POST: Add a new comment to a specified post
        """
        if not author_serial:
            return Response(
                {"detail": "Author not specified."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate that the author matches the provided `author_serial`
        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        if request.data.get("type") != "comment":
            return Response(
                {"detail": "Invalid comment type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Extract necessary fields from the request data
            post_url = request.data.get("post", "")
            post_uuid = post_url.rstrip("/").split("/")[-1]

            post = get_object_or_404(Post, uuid=post_uuid)

            comment_content = request.data.get("comment", "").strip()
            if not comment_content:
                return Response(
                    {"detail": "Comment content cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the comment
            comment = Comment.objects.create(
                content=comment_content,
                post=post,
                author=author,
                visibility="p",  # Default visibility
                uuid=uuid.uuid4(),  # Generate a new UUID for the comment
                created_by=author,
            )

            # Serialize the created comment to match the expected output format
            serializer = CommentSerializer(comment, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Post.DoesNotExist:
            return Response(
                {"detail": "Invalid post URL or UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CommentedFQIDView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve comments by FQID",
        operation_description=(
            "Fetch comments by providing the Fully Qualified ID (FQID) of the author."
            "Supports pagination for comments listing."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated comment results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of comments.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comments"
                        ),
                        "page": openapi.Schema(type=openapi.TYPE_STRING),
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "page_number": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="comment"
                                    ),
                                    "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                                    "content": openapi.Schema(type=openapi.TYPE_STRING),
                                    "contentType": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="text/markdown",
                                    ),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "id": openapi.Schema(type=openapi.TYPE_STRING),
                                    "post": openapi.Schema(type=openapi.TYPE_STRING),
                                    "page": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(description="Author not found."),
        },
        tags=["Comments"],
    )
    def get(self, request, author_fqid):
        """
        GET: Fetch comments by an author or a specific comment
        """
        author_fqid = unquote(author_fqid)
        fqid_parts = author_fqid.split("/")
        author_serial = fqid_parts[len(fqid_parts) - 1]

        if author_serial:
            # List all comments by the author
            author = get_object_or_404(AuthorProfile, user__username=author_serial)
            comments = Comment.objects.filter(author=author)
            if request.get_host() != author.user.local_node.url:
                comments = comments.filter(post__visibility__in=["p", "u"])

            # Pagination logic (~5 comments per page)
            page_size = 5
            page_number = int(request.query_params.get("page", 1))
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size

            paginated_comments = comments[start_index:end_index]

            # Total comment count
            total_count = comments.count()

            # Construct response metadata
            base_url = (
                request.build_absolute_uri("/") if request else "http://localhost/"
            )
            author_page = urljoin(base_url, f"authors/{author.user.username}")
            api_page = urljoin(base_url, f"api/authors/{author.user.username}/comments")

            # Prepare response data
            response_data = {
                "type": "comments",
                "page": author_page,
                "id": api_page,
                "page_number": page_number,
                "size": page_size,
                "count": total_count,
                "src": paginated_comments,  # Pass the queryset directly
            }

            # Serialize and return the response
            serializer = CommentsSerializer(response_data, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST
        )


class SingleCommentedView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve a single comment by FQID",
        operation_description="Fetch details of a specific comment using its Fully Qualified ID (FQID).",
        manual_parameters=[
            openapi.Parameter(
                "comment_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Details of the comment.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comment"
                        ),
                        "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "content": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="This is a sample comment.",
                        ),
                        "contentType": openapi.Schema(
                            type=openapi.TYPE_STRING, example="text/markdown"
                        ),
                        "published": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/comments/comment-uuid",
                        ),
                        "post": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/posts/post-uuid",
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/posts/post-uuid",
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Comment not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
        },
        tags=["Comments"],
    )
    def get(self, request, comment_fqid):
        """
        GET: Retrieve a single comment using its FQID.
        """
        comment_fqid = unquote(comment_fqid)
        fqid_parts = comment_fqid.split("/")
        comment_uuid = fqid_parts[len(fqid_parts) - 1]

        comment = get_object_or_404(Comment, uuid=comment_uuid)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SinglePostView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve a single post by FQID",
        operation_description="Fetch details of a specific post using its Fully Qualified ID (FQID).",
        manual_parameters=[
            openapi.Parameter(
                "post_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Details of the post.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "title": openapi.Schema(type=openapi.TYPE_STRING),
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="post"
                        ),
                        "description": openapi.Schema(type=openapi.TYPE_STRING),
                        "content": openapi.Schema(type=openapi.TYPE_STRING),
                        "visibility": openapi.Schema(type=openapi.TYPE_STRING),
                        "node": openapi.Schema(type=openapi.TYPE_STRING),
                        "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "uuid": openapi.Schema(type=openapi.TYPE_STRING),
                        "contentType": openapi.Schema(type=openapi.TYPE_STRING),
                        "created_by": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(description="Post is not public."),
            404: openapi.Response(description="Post not found."),
        },
        tags=["Posts"],
    )
    def get(self, request, post_fqid):
        """
        GET: Retrieve a single post using its FQID.
        """
        post_fqid = unquote(post_fqid)
        fqid_parts = post_fqid.split("/")
        post_uuid = fqid_parts[len(fqid_parts) - 1]

        post = get_object_or_404(Post, uuid=post_uuid)

        if post.visibility != "p":
            return Response(
                {"detail": "Post is not public."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PostSerializer(post)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostImageViewFQID(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve an image for a specific post",
        operation_description=(
            "Fetch the image content of a specific post using its Fully Qualified ID (FQID). "
            "The image can be in JPEG, PNG, or Base64 format based on the post's content type."
        ),
        manual_parameters=[
            openapi.Parameter(
                "post_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Binary image data returned successfully.",
                examples={
                    "image/jpeg": "Binary data (JPEG image)",
                    "image/png": "Binary data (PNG image)",
                },
            ),
            403: openapi.Response(
                description="Post is not public.",
                examples={
                    "application/json": {"detail": "Post is not public."},
                },
            ),
            404: openapi.Response(
                description="Post not found or image invalid.",
                examples={
                    "application/json": {"detail": "Post content is not an image."},
                },
            ),
        },
        tags=["Posts", "Images"],
    )
    def get(self, request, post_fqid):
        # Step 1: Retrieve the post
        post_fqid = unquote(post_fqid)
        fqid_parts = post_fqid.split("/")
        post_uuid = fqid_parts[len(fqid_parts) - 1]

        post = get_object_or_404(Post, uuid=post_uuid)

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


class PostCommentsView(APIView):
    """
    API View to handle fetching comments for a specific post
    """

    @swagger_auto_schema(
        operation_summary="Retrieve comments for a specific post",
        operation_description=(
            "Fetch paginated comments for a specific post, ordered by the most recent. "
            "The comments are filtered by the associated author and post ID."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author who created the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "post_serial",
                openapi.IN_PATH,
                description="UUID of the post for which comments are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated comment results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of comments for the post.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comments"
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/authors/author123/posts/post-uuid",
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/authors/author123/posts/post-uuid/comments",
                        ),
                        "page_number": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, example=20),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="comment"
                                    ),
                                    "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                                    "content": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="This is a sample comment.",
                                    ),
                                    "contentType": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="text/markdown",
                                    ),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "id": openapi.Schema(type=openapi.TYPE_STRING),
                                    "post": openapi.Schema(type=openapi.TYPE_STRING),
                                    "page": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Author or post not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
            400: openapi.Response(
                description="Invalid request.",
                examples={
                    "application/json": {"detail": "Invalid request."},
                },
            ),
        },
        tags=["Comments"],
    )
    def get(self, request, author_serial=None, post_serial=None):
        """
        GET: Retrieve comments for a specific post
        """
        # Get the author and post

        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        post = get_object_or_404(Post, uuid=post_serial, author=author)
        # Filter comments associated with the post, ordered by newest to oldest
        comments = Comment.objects.filter(post=post).order_by("-created_at")

        # Pagination logic (~5 comments per page)
        page_size = 5
        page_number = int(request.query_params.get("page", 1))
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size

        paginated_comments = comments[start_index:end_index]

        # Total comment count
        total_count = comments.count()

        # Construct response metadata
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"
        post_page = urljoin(
            base_url, f"authors/{post.author.user.username}/posts/{post.uuid}"
        )
        api_page = urljoin(
            base_url,
            f"api/authors/{post.author.user.username}/posts/{post.uuid}/comments",
        )

        # Prepare response data
        response_data = {
            "type": "comments",
            "page": post_page,
            "id": api_page,
            "page_number": page_number,
            "size": page_size,
            "count": total_count,
            "src": paginated_comments,  # Pass the queryset directly
        }

        # Serialize and return the response
        serializer = CommentsSerializer(response_data, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PostCommentsViewFQID(APIView):
    """
    API View to handle fetching comments of a specific post
    """

    @swagger_auto_schema(
        operation_summary="Retrieve comments for a specific post by FQID",
        operation_description=(
            "Fetch paginated comments for a specific post using its Fully Qualified ID (FQID), "
            "ordered by the most recent. Supports pagination."
        ),
        manual_parameters=[
            openapi.Parameter(
                "post_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated comment results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of comments for the post.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comments"
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/authors/author123/posts/post-uuid",
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/authors/author123/posts/post-uuid/comments",
                        ),
                        "page_number": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, example=20),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="comment"
                                    ),
                                    "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                                    "content": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="This is a sample comment.",
                                    ),
                                    "contentType": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="text/markdown",
                                    ),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "id": openapi.Schema(type=openapi.TYPE_STRING),
                                    "post": openapi.Schema(type=openapi.TYPE_STRING),
                                    "page": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Post not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
            400: openapi.Response(
                description="Invalid request.",
                examples={
                    "application/json": {"detail": "Invalid request."},
                },
            ),
        },
        tags=["Comments"],
    )
    def get(self, request, post_fqid):
        # Decode and extract the UUID from the FQID
        post_fqid = unquote(post_fqid)
        fqid_parts = post_fqid.split("/")
        post_uuid = fqid_parts[-1]

        # Retrieve the post using the UUID
        post = get_object_or_404(Post, uuid=post_uuid)

        # Filter comments associated with the post, ordered by newest to oldest
        comments = Comment.objects.filter(post=post).order_by("-created_at")

        # Pagination logic (~5 comments per page)
        page_size = 5
        page_number = int(request.query_params.get("page", 1))
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size

        paginated_comments = comments[start_index:end_index]

        # Total comment count
        total_count = comments.count()

        # Construct response metadata
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"
        post_page = urljoin(
            base_url, f"authors/{post.author.user.username}/posts/{post.uuid}"
        )
        api_page = urljoin(
            base_url,
            f"api/authors/{post.author.user.username}/posts/{post.uuid}/comments",
        )

        # Prepare response data
        response_data = {
            "type": "comments",
            "page": post_page,
            "id": api_page,
            "page_number": page_number,
            "size": page_size,
            "count": total_count,
            "src": paginated_comments,  # Pass the queryset directly
        }

        # Serialize and return the response
        serializer = CommentsSerializer(response_data, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RemoteCommentView(APIView):
    """
    GET: Retrieve a specific comment using its remote FQID
    """

    @swagger_auto_schema(
        operation_summary="Retrieve a specific remote comment by FQID",
        operation_description=(
            "Fetch details of a specific comment using the author's username, the post's UUID, and the comment's remote Fully Qualified ID (FQID)."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author associated with the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "post_serial",
                openapi.IN_PATH,
                description="UUID of the post associated with the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "remote_comment_fqid",
                openapi.IN_PATH,
                description="Remote Fully Qualified ID (FQID) of the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Details of the specific comment.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="comment"
                        ),
                        "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "content": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="This is a sample comment.",
                        ),
                        "contentType": openapi.Schema(
                            type=openapi.TYPE_STRING, example="text/markdown"
                        ),
                        "published": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/comments/comment-uuid",
                        ),
                        "post": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/posts/post-uuid",
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/posts/post-uuid",
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Author, post, or comment not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
        },
        tags=["Comments"],
    )
    def get(self, request, author_serial, post_serial, remote_comment_fqid):

        # Decode the remote_comment_fqid
        remote_comment_fqid = unquote(remote_comment_fqid)
        fqid_parts = remote_comment_fqid.split("/")
        comment_uuid = fqid_parts[len(fqid_parts) - 1]

        # Retrieve the author to ensure they exist
        author = get_object_or_404(AuthorProfile, user__username=author_serial)

        # Retrieve the post associated with the author
        post = get_object_or_404(Post, uuid=post_serial, author=author)

        comment = get_object_or_404(Comment, uuid=comment_uuid, post=post)

        serializer = CommentSerializer(comment)

        return Response(serializer.data, status=status.HTTP_200_OK)


class PostLikesAPIView(APIView):
    """
    Endpoint to retrieve likes on a specific post of a specific author.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve likes on a specific post",
        operation_description=(
            "Fetch likes on a specific post by its UUID. Supports pagination for likes."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author who created the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "post_uuid",
                openapi.IN_PATH,
                description="UUID of the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated likes results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of likes on the post.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(type=openapi.TYPE_STRING),
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "page": openapi.Schema(type=openapi.TYPE_STRING),
                        "page_number": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="like"
                                    ),
                                    "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "id": openapi.Schema(type=openapi.TYPE_STRING),
                                    "object": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(description="Post or likes not found."),
        },
        tags=["Likes"],
    )
    def get(self, request, author_serial, post_uuid):

        author = get_object_or_404(AuthorProfile, user__username=author_serial)

        # Retrieve the post associated with the author
        post = get_object_or_404(Post, uuid=post_uuid, author=author)

        # Get all likes on the post
        likes = Like.objects.filter(post=post).order_by("-created_at")

        # Paginate the results (5 likes per page)
        paginator = Paginator(likes, 5)
        page_number = request.query_params.get("page", 1)
        page = paginator.get_page(page_number)

        # Serialize the results
        serializer = LikeSerializer(page.object_list, many=True)

        # Construct the response body
        response_data = {
            "type": "likes",
            "id": f"http://{request.get_host()}/api/authors/{author_serial}/posts/{post_uuid}/likes",
            "page": f"http://{request.get_host()}/authors/{author_serial}/posts/{post_uuid}",
            "page_number": page.number,
            "size": paginator.per_page,
            "count": paginator.count,
            "src": serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PostLikesFQIDAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve all likes for a specific post by FQID",
        operation_description=(
            "Fetch paginated likes for a specific post using its Fully Qualified ID (FQID). "
            "Supports pagination for the likes."
        ),
        manual_parameters=[
            openapi.Parameter(
                "post_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the post.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated likes results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of likes for the post.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="likes"
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/authors/author123/posts/post-uuid/likes",
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/authors/author123/posts/post-uuid",
                        ),
                        "page_number": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, example=20),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="like"
                                    ),
                                    "author": openapi.Schema(type=openapi.TYPE_OBJECT),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="http://localhost/api/likes/like-uuid",
                                    ),
                                    "object": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="http://localhost/api/posts/post-uuid",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Post not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
            400: openapi.Response(
                description="Invalid request.",
                examples={
                    "application/json": {"detail": "Invalid request."},
                },
            ),
        },
        tags=["Likes"],
    )
    def get(self, request, post_fqid):
        """
        GET: Retrieve all likes for a specific post based on fqid
        """
        post_fqid = unquote(post_fqid)
        fqid_parts = post_fqid.split("/")
        post_uuid = fqid_parts[len(fqid_parts) - 1]

        post = get_object_or_404(Post, uuid=post_uuid)

        likes = Like.objects.filter(post=post).order_by("-created_at")

        author_serial = post.author.user.username
        # Paginate the results (5 likes per page)
        paginator = Paginator(likes, 5)
        page_number = request.query_params.get("page", 1)
        page = paginator.get_page(page_number)

        # Serialize the results
        serializer = LikeSerializer(page.object_list, many=True)

        # Construct the response body
        response_data = {
            "type": "likes",
            "id": f"http://{request.get_host()}/api/authors/{author_serial}/posts/{post_uuid}/likes",
            "page": f"http://{request.get_host()}/authors/{author_serial}/posts/{post_uuid}",
            "page_number": page.number,
            "size": paginator.per_page,
            "count": paginator.count,
            "src": serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CommentLikesView(APIView):
    """
    Endpoint to retrieve likes for a specific comment. Always returns a likes object with a count of zero.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve likes for a specific comment",
        operation_description=(
            "Fetch likes for a specific comment using the author's username, post's UUID, "
            "and comment's Fully Qualified ID (FQID). Always returns a count of zero likes."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author associated with the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "post_serial",
                openapi.IN_PATH,
                description="UUID of the post associated with the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "comment_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the comment.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Likes object for the specified comment (count is always zero).",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="likes"
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/authors/author123/posts/post-uuid/comments/comment-uuid/likes",
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/authors/author123/posts/post-uuid/comments/comment-uuid/likes",
                        ),
                        "page_number": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, example=0),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                            example=[],  # Always empty
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Comment not found.",
                examples={
                    "application/json": {"detail": "Comment not found."},
                },
            ),
        },
        tags=["Likes"],
    )
    def get(self, request, author_serial, post_serial, comment_fqid):
        try:
            # Verify the comment exists
            comment_fqid = unquote(comment_fqid)
            fqid_parts = comment_fqid.split("/")
            comment_uuid = fqid_parts[len(fqid_parts) - 1]

            post = get_object_or_404(Post, uuid=post_serial)

            Comment.objects.get(uuid=comment_uuid, post=post)
        except Comment.DoesNotExist:
            return Response(
                {"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Response data with count always zero
        response_data = {
            "type": "likes",
            "id": f"http://{request.get_host()}/api/authors/{author_serial}/posts/{post_serial}/comments/{comment_fqid}/likes",
            "page": f"http://{request.get_host()}/authors/{author_serial}/posts/{post_serial}/comments/{comment_fqid}/likes",
            "page_number": 1,
            "size": 5,
            "count": 0,
            "src": [],  # Always empty since there will be no likes
        }

        return Response(response_data, status=status.HTTP_200_OK)


class SingleLikeView(APIView):
    """
    Endpoint to retrieve a single like object by its LIKE_SERIAL.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve a single like by LIKE_SERIAL",
        operation_description=(
            "Fetch details of a specific like object using the author's username and the like's UUID (LIKE_SERIAL)."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author associated with the like.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "like_serial",
                openapi.IN_PATH,
                description="UUID of the like object to retrieve.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Details of the specific like object.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="like"
                        ),
                        "author": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="http://localhost/api/authors/author123",
                                ),
                                "displayName": openapi.Schema(
                                    type=openapi.TYPE_STRING, example="John Doe"
                                ),
                                "host": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="http://localhost/",
                                ),
                                "github": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="https://github.com/johndoe",
                                ),
                                "profileImage": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="http://localhost/images/avatar.jpg",
                                ),
                            },
                        ),
                        "published": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format="date-time",
                            example="2024-11-16T10:00:00Z",
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/likes/like-uuid",
                        ),
                        "object": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/posts/post-uuid",
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Like or author not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
        },
        tags=["Likes"],
    )
    def get(self, request, author_serial, like_serial):
        # Fetch the author to validate the URL
        author = get_object_or_404(AuthorProfile, user__username=author_serial)

        # Fetch the Like object by its UUID (like_serial)
        like = get_object_or_404(Like, uuid=like_serial, author=author)

        # Serialize the Like object
        serializer = LikeSerializer(like, context={"request": request})

        # Return the serialized Like object
        return Response(serializer.data, status=status.HTTP_200_OK)


class ThingsLikedByAuthorView(APIView):
    """
    Endpoint to retrieve a list of things liked by a specific author.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve things liked by an author",
        operation_description=(
            "Fetch a paginated list of all the things liked by a specific author, "
            "identified by their username."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_serial",
                openapi.IN_PATH,
                description="Username of the author whose liked objects are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of things liked by the author.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="likes"
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/authors/author123/liked",
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/authors/author123/liked",
                        ),
                        "page_number": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, example=10),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="like"
                                    ),
                                    "author": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "id": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="http://localhost/api/authors/author123",
                                            ),
                                            "displayName": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="John Doe",
                                            ),
                                            "host": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="http://localhost/",
                                            ),
                                            "github": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="https://github.com/johndoe",
                                            ),
                                            "profileImage": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="http://localhost/images/avatar.jpg",
                                            ),
                                        },
                                    ),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format="date-time",
                                        example="2024-11-16T10:00:00Z",
                                    ),
                                    "id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="http://localhost/api/likes/like-uuid",
                                    ),
                                    "object": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="http://localhost/api/posts/post-uuid",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Author not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
        },
        tags=["Likes"],
    )
    def get(self, request, author_serial):
        # Retrieve the author by serial
        author = get_object_or_404(AuthorProfile, user__username=author_serial)

        # Fetch all likes made by the author
        likes = Like.objects.filter(author=author).order_by("-created_at")

        # Paginate the results (5 likes per page)
        paginator = Paginator(likes, 5)
        page_number = request.query_params.get("page", 1)
        page = paginator.get_page(page_number)

        # Serialize the likes in the current page
        serializer = LikeSerializer(page.object_list, many=True)

        # Construct the response body
        response_data = {
            "type": "likes",
            "id": f"http://{request.get_host()}/api/authors/{author_serial}/liked",
            "page": f"http://{request.get_host()}/authors/{author_serial}/liked",
            "page_number": page.number,
            "size": paginator.per_page,
            "count": paginator.count,
            "src": serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class SingleLikeFQIDView(APIView):
    """
    Endpoint to retrieve a single like object by its LIKE_SERIAL.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve a single like by LIKE_SERIAL",
        operation_description=(
            "Fetch details of a specific like object using its Fully Qualified ID (FQID)."
        ),
        manual_parameters=[
            openapi.Parameter(
                "like_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the like.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Details of the specific like object.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="like"
                        ),
                        "author": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="http://localhost/api/authors/author123",
                                ),
                                "displayName": openapi.Schema(
                                    type=openapi.TYPE_STRING, example="John Doe"
                                ),
                                "host": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="http://localhost/",
                                ),
                                "github": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="https://github.com/johndoe",
                                ),
                                "profileImage": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="http://localhost/images/avatar.jpg",
                                ),
                            },
                        ),
                        "published": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format="date-time",
                            example="2024-11-16T10:00:00Z",
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/likes/like-uuid",
                        ),
                        "object": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/posts/post-uuid",
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Like object not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
        },
        tags=["Likes"],
    )
    def get(self, request, like_fqid):
        # Fetch the author to validate the URL
        like_fqid = unquote(like_fqid)
        fqid_parts = like_fqid.split("/")
        like_uuid = fqid_parts[len(fqid_parts) - 1]

        # Fetch the Like object by its UUID (like_serial)
        like = get_object_or_404(Like, uuid=like_uuid)

        # Serialize the Like object
        serializer = LikeSerializer(like, context={"request": request})

        # Return the serialized Like object
        return Response(serializer.data, status=status.HTTP_200_OK)


class ThingsLikedByAuthorFQIDView(APIView):
    """
    Endpoint to retrieve a list of things liked by a specific author.
    """

    @swagger_auto_schema(
        operation_summary="Retrieve things liked by an author (FQID)",
        operation_description=(
            "Fetch a paginated list of all the things liked by a specific author, "
            "identified by their Fully Qualified ID (FQID)."
        ),
        manual_parameters=[
            openapi.Parameter(
                "author_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the author whose liked objects are to be retrieved.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number for paginated results.",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Paginated list of things liked by the author.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING, example="likes"
                        ),
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/api/authors/author123/liked",
                        ),
                        "page": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="http://localhost/authors/author123/liked",
                        ),
                        "page_number": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "size": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER, example=10),
                        "src": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="like"
                                    ),
                                    "author": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "id": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="http://localhost/api/authors/author123",
                                            ),
                                            "displayName": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="John Doe",
                                            ),
                                            "host": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="http://localhost/",
                                            ),
                                            "github": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="https://github.com/johndoe",
                                            ),
                                            "profileImage": openapi.Schema(
                                                type=openapi.TYPE_STRING,
                                                example="http://localhost/images/avatar.jpg",
                                            ),
                                        },
                                    ),
                                    "published": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format="date-time",
                                        example="2024-11-16T10:00:00Z",
                                    ),
                                    "id": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="http://localhost/api/likes/like-uuid",
                                    ),
                                    "object": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="http://localhost/api/posts/post-uuid",
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="Author not found.",
                examples={
                    "application/json": {"detail": "Not found."},
                },
            ),
        },
        tags=["Likes"],
    )
    def get(self, request, author_fqid):
        # Retrieve the author by serial

        author_fqid = unquote(author_fqid)
        fqid_parts = author_fqid.split("/")
        author_serial = fqid_parts[len(fqid_parts) - 1]

        author = get_object_or_404(AuthorProfile, user__username=author_serial)

        # Fetch all likes made by the author
        likes = Like.objects.filter(author=author).order_by("-created_at")

        # Paginate the results (5 likes per page)
        paginator = Paginator(likes, 5)
        page_number = request.query_params.get("page", 1)
        page = paginator.get_page(page_number)

        # Serialize the likes in the current page
        serializer = LikeSerializer(page.object_list, many=True)

        # Construct the response body
        response_data = {
            "type": "likes",
            "id": f"http://{request.get_host()}/api/authors/{author_serial}/liked",
            "page": f"http://{request.get_host()}/authors/{author_serial}/liked",
            "page_number": page.number,
            "size": paginator.per_page,
            "count": paginator.count,
            "src": serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)
