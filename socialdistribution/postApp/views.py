# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

# Third-party imports
from rest_framework import generics, permissions
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
from .serializers import PostSerializer

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


# --- API Views ---
class IsAuthorOrReadOnly(BasePermission):
    """
    Custom permission to only allow authors of a post to edit or delete it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the author of the post.
        return obj.author.user == request.user


class PostDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a public post or friends-only post if authenticated.
    PUT: Update a post if authenticated as the author.
    DELETE: Delete a post if authenticated as the author.
    """

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthorOrReadOnly]

    def get_object(self):
        author_serial = self.kwargs["author_serial"]
        post_serial = self.kwargs["post_serial"]
        # Get the author
        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        # Get the post
        post = get_object_or_404(Post, uuid=post_serial, author=author)

        # Check visibility
        if post.visibility == "p":  # Public
            return post
        elif post.visibility == "fo":  # Friends-only
            if self.request.user.is_authenticated:
                # Check if the user is a friend
                if is_friend(self.request.user.author_profile, author):
                    return post
            raise PermissionDenied("You do not have permission to access this post.")
        else:
            raise Http404

    def perform_update(self, serializer):
        # Ensure the user is the author
        if self.request.user.author_profile != serializer.instance.author:
            raise PermissionDenied("You do not have permission to edit this post.")
        serializer.save()

    def perform_destroy(self, instance):
        # Ensure the user is the author
        if self.request.user.author_profile != instance.author:
            raise PermissionDenied("You do not have permission to delete this post.")
        instance.delete()


class PostListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: Retrieve recent posts from an author.
    POST: Create a new post as the authenticated author.
    """

    serializer_class = PostSerializer

    def get_queryset(self):
        author_serial = self.kwargs["author_serial"]
        author = get_object_or_404(AuthorProfile, user__username=author_serial)
        user = self.request.user

        # Not authenticated: only public posts.
        if not user.is_authenticated:
            return Post.objects.filter(author=author, visibility="p")

        # Authenticated as the author: all posts.
        if user.author_profile == author:
            return Post.objects.filter(author=author)

        # Authenticated as friend: public + friends-only posts.
        if is_friend(user.author_profile, author):
            return Post.objects.filter(author=author).exclude(visibility="u")

        # Authenticated but not a friend: only public posts.
        return Post.objects.filter(author=author, visibility="p")

    def perform_create(self, serializer):
        author_serial = self.kwargs["author_serial"]
        author = get_object_or_404(AuthorProfile, user__username=author_serial)

        # Ensure the authenticated user is the author
        if self.request.user.author_profile != author:
            raise PermissionDenied("You cannot create posts for another author.")

        serializer.save(author=author, node=author.local_node)


class PostByFQIDAPIView(APIView):
    """
    GET: Retrieve a public post by its Fully Qualified ID (FQID).
    """

    def get(self, request, post_fqid):
        # Decode the FQID to get the post
        try:
            # post_url = f"http://{request.get_host()}/api/posts/{post_fqid}"
            post = Post.objects.get(uuid=post_fqid)
        except Exception as exc:
            raise Http404 from exc

        # Check visibility
        if post.visibility == "p":  # Public
            serializer = PostSerializer(post)
            return Response(serializer.data)
        elif post.visibility == "fo":  # Friends-only
            if request.user.is_authenticated:
                # Check if the user is a friend
                if is_friend(request.user.author_profile, post.author):
                    serializer = PostSerializer(post)
                    return Response(serializer.data)
            raise PermissionDenied("You do not have permission to access this post.")
        else:
            raise Http404


def is_friend(author1, author2):
    # Implement logic to check if author1 and author2 are friends
    friendship_exists = Friends.objects.filter(
        (Q(user1=author1) & Q(user2=author2)) | (Q(user1=author2) & Q(user2=author1)),
        status=True,
    ).exists()
    return friendship_exists
