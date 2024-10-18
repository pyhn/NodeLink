# from django.shortcuts import render, HttpResponse

# Create your views here.
# def home(request):
#     return render(request, "home.html")

from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from node_link.models import Post, Friends, Follower, Comment, Like, Author
from .forms import SignUpForm, LoginForm
import random

User = get_user_model()


@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title", "New Post")
        content = request.POST.get("content", "")
        img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility", "p")
        author = Author.objects.get(pk=request.user.pk)

        # Create the post with the necessary fields
        Post.objects.create(
            title=title,
            content=content,
            img=img,
            visibility=visibility,
            author=author,
            node=author.local_node,  # Associate the post with the author's node
            created_by=author,
            updated_by=author,
        )
        # Redirect to the post list page SEdBo49hPQ4
        return redirect("post_list")

    return render(request, "create_post.html")


def post_list(request):
    # Retrieve all posts
    posts = Post.objects.all()
    return render(request, "post_list.html", {"posts": posts})


@login_required
def create_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        content = request.POST.get("content")

        author = Author.objects.get(pk=request.user.pk)

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
        return redirect("post_detail", post_id=post.id)

    return render(request, "create_comment.html", {"post": post})


@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    author = Author.objects.get(pk=request.user.pk)

    existing_like = Like.objects.filter(post=post, author=author)
    if existing_like.exists():
        existing_like.delete()
    else:
        Like.objects.create(
            post=post,
            author=author,  # Include the author field
            created_by=author,
            updated_by=author,
        )

    return redirect("post_detail", post_id=post.id)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set additional fields
            user.email = form.cleaned_data["email"]
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            # user.username = form.cleaned_data['username']
            user.description = form.cleaned_data["description"]
            user.save()
            auth_login(request, user)
            messages.success(
                request, f"Welcome {user.username}, your account has been created."
            )
            return redirect("home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, f"Welcome back, {form.get_user().username}!")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


@login_required
def post_card(request, u_id):
    """reders a single card

    Args:
        request (_type_): _description_
        id (_type_): _description_

    Returns:
        _type_: _description_
    """
    post = get_object_or_404(Post, uuid=u_id)
    # check is user has permission to see post
    if post.visibility == "p" or (
        post.visibility == "fo"
        and Friends.objects.filter(
            Q(user1=request.user, user2=post.user)
            | Q(user2=request.user, user1=post.user)
        ).exists()
    ):

        user_has_liked = post.likes.filter(author=request.user).exists()
        user_img = post.author.profile_image

        context = {
            "post": post,
            "user_has_liked": user_has_liked,
            "profile_img": user_img,
        }
        return render(request, "post_card.html", context)
    return redirect(request.META.get("HTTP_REFERER"))  #!!!error page?


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user_has_liked = False

    if request.user.is_authenticated:
        try:
            author = Author.objects.get(pk=request.user.pk)
            user_has_liked = post.likes.filter(author=author).exists()
        except Author.DoesNotExist:
            # Handle the case where the Author profile does not exist
            messages.error(request, "Author profile not found.")
            # Optionally, redirect or set user_has_liked to False
            redirect("post_list")

    user_has_liked = post.likes.filter(author=author).exists()

    return render(
        request,
        "post_detail.html",
        {
            "post": post,
            "user_has_liked": user_has_liked,
        },
    )


@login_required
def home(request):

    if request.method == "GET":
        template_name = "home.html"
        user = request.user
        friends = list(
            Friends.objects.filter(
                Q(user1=user, status=True) | Q(user2=user, status=True)
            ).values_list("user1", "user2")
        )
        friends = list(set(u_id for tup in friends for u_id in tup))
        following = list(Follower.objects.filter(Q(user2=user)).values_list())

        # Get public posts
        public_posts = list(
            Post.objects.filter(visibility="p", created_at__gt=user.last_login)
            .distinct()
            .values_list("uuid", flat=True)
        )

        # Get friends-only posts from the user's friends
        fo_posts = list(
            Post.objects.filter(
                visibility="fo", author__in=friends, created_at__gt=user.last_login
            )
            .distinct()
            .values_list("uuid", flat=True)
        )

        fl_posts = list(
            Post.objects.filter(
                visibility="fo", author__in=following, created_at__gt=user.last_login
            )
            .distinct()
            .values_list("uuid", flat=True)
        )

        # Combine and sort all posts by creation date
        newest = list(set(public_posts + fo_posts + fl_posts))
        random.shuffle(newest)

        rest_post = list(
            Post.objects.filter(visibility="p", created_at__lt=user.last_login)
            .distinct()
            .values_list("uuid", flat=True)
        )
        random.shuffle(rest_post)
        all_posts = set(newest + rest_post)

        context = {"all_ids": all_posts}

        # Return the rendered template
        return render(request, template_name, context)


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("login")
