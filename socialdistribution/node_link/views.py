from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Post, AuthorProfile, Comment, Like, Node
from .forms import SignUpForm, LoginForm
import uuid  # If using uuid for unique dummy usernames

User = get_user_model()


@login_required
def create_post(request):
    if not hasattr(request.user, "author_profile"):
        messages.error(request, "You are not authorized to create posts.")
        return redirect("home")

    author = request.user.author_profile

    if request.method == "POST":
        title = request.POST.get("title", "New Post")
        content = request.POST.get("content", "")
        img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility", "p")

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


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user_has_liked = False

    if request.user.is_authenticated and hasattr(request.user, "author_profile"):
        author = request.user.author_profile
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
def create_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if not hasattr(request.user, "author_profile"):
        messages.error(request, "You are not authorized to comment on posts.")
        return redirect("post_detail", post_id=post_id)

    author = request.user.author_profile

    if request.method == "POST":
        content = request.POST.get("content")

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
        return redirect("post_detail", id=post.id)

    return render(request, "create_comment.html", {"post": post})


@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if not hasattr(request.user, "author_profile"):
        messages.error(request, "You are not authorized to like posts.")
        return redirect("post_detail", post_id=post_id)

    author = request.user.author_profile

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

    return redirect("post_detail", id=post.id)


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

            # Retrieve the first node in the Node table
            first_node = Node.objects.first()
            if not first_node:
                messages.error(request, "No nodes are available to assign.")
                return redirect("signup")

            # Create an AuthorProfile linked to the user and assign the first node
            AuthorProfile.objects.create(
                user=user,
                local_node=first_node,
                # Set other author-specific fields if necessary
            )

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


@login_required(
    login_url="login"
)  # Ensure 'login' matches the name of your login URL pattern
def home_view(request):
    return render(request, "home.html")


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("login")
