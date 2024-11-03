# Django imports
import uuid
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets, permissions
from .serializers import PostSerializer, CommentSerializer, LikeSerializer
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse


# Third-party imports
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

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


# renders the form for sharing the post to other authors
@login_required
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


@login_required
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
