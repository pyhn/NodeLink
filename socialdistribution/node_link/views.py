# from django.shortcuts import render, HttpResponse


from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import get_user_model
from node_link.models import Post, Friends, Follower, Comment, Like, AuthorProfile, Node
from .forms import SignUpForm, LoginForm

User = get_user_model()
# sign up
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


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("login")


def has_access(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if (
        post.author.id == request.user.author_profile.id
        or post.visibility == "p"
        or post.visibility == "u"
        or (
            post.visibility == "fo"
            and Friends.objects.filter(
                Q(user1=request.user.author_profile, user2=post.author)
                | Q(user2=request.user.author_profile, user1=post.author)
            ).exists()
        )
    ):
        return True
    return False


# post edit/create methods


@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title", "New Post")
        content = request.POST.get("content", "")
        img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility", "p")
        author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

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
        return redirect("home")

    return render(request, "create_post.html")


@login_required
def create_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

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
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)

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


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    # check if they are allow to delete
    if post.author.user == request.user:
        post.visibility = "d"
    return redirect("home")


# view post


def post_list(request):
    # Retrieve all posts
    posts = Post.objects.all()
    return render(request, "post_list.html", {"posts": posts})


@login_required
def post_card(request, u_id):
    """reders a single card

    Args:
        request (_type_): _description_
        id (_type_): _description_

    Returns:
        _type_: _description_
    """
    post = get_object_or_404(Post, id=u_id)
    # check is user has permission to see post
    if has_access(request=request, post_id=u_id):

        user_has_liked = post.likes.filter(author=request.user.author_profile).exists()
        user_img = post.author.user.profile_image

        context = {
            "post": post,
            "user_has_liked": user_has_liked,
            "profile_img": user_img,
        }
        return render(request, "post_card.html", context)
    return HttpResponseForbidden("You are not supposed to be here. Go Home!")


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if has_access(request=request, post_id=post_id):
        user_has_liked = False

        if request.user.is_authenticated:
            try:
                author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
                user_has_liked = post.likes.filter(author=author).exists()
            except AuthorProfile.DoesNotExist:
                # Handle the case where the Author profile does not exist
                messages.error(request, "Author profile not found.")
                # Optionally, redirect or set user_has_liked to False
                redirect("post_list")

        user_has_liked = post.likes.filter(author=author.id).exists()
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


@login_required
def home(request):

    if request.method == "GET":
        template_name = "home.html"
        user = request.user.author_profile
        friends = list(
            Friends.objects.filter(
                Q(user1=user, status=True) | Q(user2=user, status=True)
            ).values_list("user1", "user2")
        )
        friends = list(set(u_id for tup in friends for u_id in tup))
        following = list(Follower.objects.filter(Q(user2=user)).values_list())

        # Get all posts
        all_posts = list(
            Post.objects.filter(
                Q(visibility="p")  # all public
                | Q(
                    visibility="fo",  # all friends only
                    author_id__in=friends,
                )
                | Q(
                    visibility="u",  # all unlisted
                    author_id__in=following,
                )
            )
            .distinct()
            .order_by("-created_at")
            .values_list("id", flat=True)
        )

        context = {"all_ids": all_posts}

        # Return the rendered template
        return render(request, template_name, context)
    return HttpResponseNotAllowed("Invalid Method;go home")
