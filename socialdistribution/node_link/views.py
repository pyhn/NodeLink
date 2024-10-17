# from django.shortcuts import render, HttpResponse

# Create your views here.
# def home(request):
#     return render(request, "home.html")

from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse
import base64


from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from node_link.models import Post, Friends, Follower, Comment, Like


from .forms import SignUpForm, LoginForm
import random

User = get_user_model()


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


def post_card(request, e_id):
    """reders a single card

    Args:
        request (_type_): _description_
        id (_type_): _description_

    Returns:
        _type_: _description_
    """
    post = Post.objects.filter(pk=e_id).first()
    # check is user has permission to see post
    if post.visibility == "p" or (
        post.visibility == "fo"
        and Friends.objects.filter(
            Q(user1=request.user, user2=post.user)
            | Q(user2=request.user, user1=post.user)
        ).exists()
    ):

        comment_num = Comment.objects.filter(post=post).count()
        like_num = Like.objects.filter(post=post).count()

        context = {
            "username": post.author.username,
            "post_title": post.title,
            "post_img": post.img.url if post.img else False,
            "post_content": post.content if post.content else False,
            "likes_num": like_num,
            "comments_num": comment_num,
            "fo": True if post.visibility == "fo" else False,
        }
        return render(request, "post_card.html", context)
    return redirect(request.META.get("HTTP_REFERER"))  #!!!error page?


class Home(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get(self, request):
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
            .values_list("pk", flat=True)
        )

        # Get friends-only posts from the user's friends
        fo_posts = list(
            Post.objects.filter(
                visibility="fo", author__in=friends, created_at__gt=user.last_login
            )
            .distinct()
            .values_list("pk", flat=True)
        )

        fl_posts = list(
            Post.objects.filter(
                visibility="fo", author__in=following, created_at__gt=user.last_login
            )
            .distinct()
            .values_list("pk", flat=True)
        )

        # Combine and sort all posts by creation date
        all_posts = public_posts + fo_posts + fl_posts
        all_posts = list(set(all_posts))
        random.shuffle(all_posts)

        context = {"all_ids": all_posts}

        # Return the rendered template
        return render(request, self.template_name, context)


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("login")
