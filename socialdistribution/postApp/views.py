# Django imports
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets
from .serializers import PostSerializer, CommentSerializer, LikeSerializer
from rest_framework.permissions import IsAuthenticated


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


@is_approved
def create_post(request):
    return render(request, "create_post.html")


@is_approved
def submit_post(request):
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
                    return redirect("postApp:create_post")  # Early exit
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
    return redirect("node_link:home")


@is_approved
def create_comment(request, username, post_uuid ):
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

    return redirect("postApp:post_detail", post_uuid=post_uuid)


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
def post_detail(request, username,  post_uuid: str):
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
        link_url = reverse("postApp:post_detail", args=[post.uuid])
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
