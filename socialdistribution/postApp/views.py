# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions

# Project imports
from node_link.models import Notification
from node_link.utils.common import has_access
from authorApp.models import AuthorProfile
from postApp.models import Post, Comment, Like  # ,CommentLike !!!POST NOTE
from .utils.image_checks import validate_image_file, process_image_file

# Package imports
import commonmark
from datetime import datetime


@login_required
def create_post(request):
    return render(request, "create_post.html")


@login_required
def submit_post(request):
    if request.method != "POST":
        return redirect("postApp:create_post")

    # Extract form data with defaults
    title = request.POST.get("title", "New Post")
    description = request.POST.get("description", "")
    content = request.POST.get("content", "")
    visibility = request.POST.get("visibility", "p")
    content_type = request.POST.get("contentType", "p")
    submit_type = request.POST.get("submit_type", "plain")

    try:
        if submit_type == "image":
            img = request.FILES.get("img", None)
            if img:
                validate_image_file(img)
                data_url, actual_content_type = process_image_file(img)
                if content_type != actual_content_type:
                    raise ValidationError("MIME type does not match contentType.")
                content = data_url
                content_type = actual_content_type
            else:
                raise ValidationError("Image file is required for image posts.")

        author = request.user.author_profile
        post = Post.objects.create(
            title=title,
            description=description,
            content=content,
            visibility=visibility,
            contentType=content_type,
            author=author,
            node=author.local_node,
            created_by=author,
            updated_by=author,
        )

        messages.success(request, "Post created successfully!")
        return redirect("postApp:post_detail", post_uuid=post.uuid)

    except ValidationError:
        return redirect("postApp:create_post")


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


@login_required
def edit_post(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)

    if post.author.user != request.user:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    # Determine active tab based on contentType
    if post.contentType == "p":
        active_tab = "PlainText"
    elif post.contentType == "m":
        active_tab = "Markdown"
    elif post.contentType in ["png", "jpeg", "gif"]:
        active_tab = "Image"
    else:
        active_tab = "PlainText"  # Default to PlainText if unknown

    # Define image types for conditional rendering
    image_types = ["png", "jpeg", "gif"]

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


@login_required
def submit_edit_post(request, post_uuid):
    post = get_object_or_404(Post, uuid=post_uuid)

    if post.author.user != request.user:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if request.method != "POST":
        return redirect("postApp:edit_post", post_uuid=post_uuid)

    # Extract form data with defaults
    title = request.POST.get("title", post.title)
    description = request.POST.get("description", post.description)
    content = request.POST.get("content", post.content)
    visibility = request.POST.get("visibility", post.visibility)
    content_type = request.POST.get("contentType", post.contentType)
    submit_type = request.POST.get("submit_type", "plain")  # From updated form

    try:
        if submit_type == "image":
            img = request.FILES.get("img", None)
            if img:
                # Validate the image
                validate_image_file(img)

                # Process the image and update content and content_type
                data_url, actual_content_type = process_image_file(img)

                # Ensure content_type matches actual_content_type
                if content_type != actual_content_type:
                    raise ValidationError("MIME type does not match contentType.")

                content = data_url
                content_type = actual_content_type
            else:
                # If no new image is uploaded, retain existing content
                content = post.content
                # Optionally, reset content_type if the original post was an image
                # For example:
                # if post.contentType in ['png', 'jpeg', 'gif']:
                #     content_type = 'a'
        # For non-image submissions, no additional handling is required

        # Update the post with new data
        post.title = title
        post.description = description
        post.content = content
        post.visibility = visibility
        post.contentType = content_type
        post.updated_by = request.user.author_profile
        post.updated_at = datetime.now()
        post.save()

        messages.success(request, "Post updated successfully!")
        return redirect("postApp:post_detail", post_uuid=post_uuid)

    except ValidationError as e:
        # Handle validation errors and inform the user
        messages.error(request, e.message)
        return redirect("postApp:edit_post", post_uuid=post_uuid)


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
