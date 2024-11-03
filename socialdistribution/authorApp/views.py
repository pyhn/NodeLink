# Django Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseNotAllowed

# Project Imports
from .models import (
    Friends,
    Follower,
    AuthorProfile,
)
from node_link.models import Node
from .forms import SignUpForm, LoginForm
from node_link.utils.common import has_access
from postApp.models import Post

# Third Party Imports
from datetime import datetime

# Create your views here.
# sign up
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("node_link:home")
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
                return redirect("authorApp:signup")

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
            return redirect("node_link:home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("node_link:home")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, f"Welcome back, {form.get_user().username}!")
            return redirect("node_link:home")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("authorApp:login")


@login_required
def profile_display(request, author_un):
    if request.method == "GET":
        author = get_object_or_404(AuthorProfile, user__username=author_un)
        all_ids = list(Post.objects.filter(author=author).order_by("-created_at"))
        num_following = Follower.objects.filter(actor=author).count()
        num_friends = Friends.objects.filter(
            Q(user1=author, status=True) | Q(user2=author, status=True)
        ).count()
        num_followers = Follower.objects.filter(object=author).count()

        filtered_ids = []
        for a in all_ids:
            if has_access(request, a.uuid):
                filtered_ids.append(a)

        context = {
            "all_ids": filtered_ids,
            "num_following": num_following,
            "num_friends": num_friends,
            "num_followers": num_followers,
            "author": author,
        }
        return render(request, "user_profile.html", context)
    return redirect("node_link:home")


@login_required
def approve_follow_request(request, follow_request_id):
    follow_request = get_object_or_404(
        Follower, id=follow_request_id, user2=request.user.author_profile
    )
    follow_request.status = "approved"
    follow_request.save()
    return redirect("node_link:notifications")


@login_required
def deny_follow_request(request, follow_request_id):
    follow_request = get_object_or_404(
        Follower, id=follow_request_id, user2=request.user.author_profile
    )
    follow_request.status = "denied"
    follow_request.save()
    return redirect("node_link:notifications")


@login_required
def friends_page(request):
    """
    Renders a page listing all authors with a 'Follow' button next to each.
    Separates authors into those you can follow, those you are already following,
    and those who are your friends.
    """
    current_author = request.user.author_profile

    # Exclude the current user from the list
    authors = AuthorProfile.objects.exclude(user=request.user).select_related("user")

    # Get a list of author IDs that the current user is already following (status='A')
    following_ids = Follower.objects.filter(
        user1=current_author, status="A"
    ).values_list("user2_id", flat=True)

    # Get a list of author IDs that the current user has pending follow requests with (status='P')
    pending_request_ids = Follower.objects.filter(
        user1=current_author, status="P"
    ).values_list("user2_id", flat=True)

    # Get a list of author IDs that have denied follow requests (status='D')
    denied_request_ids = Follower.objects.filter(
        user1=current_author, status="D"
    ).values_list("user2_id", flat=True)

    # Get a list of friend IDs
    friend_ids = Friends.objects.filter(
        Q(user1=current_author) | Q(user2=current_author)
    ).values_list("user1_id", "user2_id")

    # Flatten the list of tuples and remove current_author's ID
    flat_friend_ids = set()
    for pair in friend_ids:
        flat_friend_ids.update(pair)
    flat_friend_ids.discard(current_author.id)

    # Authors the user can follow (not already following, no pending requests, and not already friends)
    can_follow_authors = (
        authors.exclude(id__in=following_ids)
        .exclude(id__in=pending_request_ids)
        .exclude(id__in=flat_friend_ids)
    )

    # Authors the user is already following (including friends)
    already_following_authors = authors.filter(id__in=following_ids)
    # Removed .exclude(id__in=flat_friend_ids)

    # Authors with denied follow requests (allow resending follow requests)
    denied_follow_authors = authors.filter(id__in=denied_request_ids).exclude(
        id__in=flat_friend_ids
    )

    # Friends
    friends = AuthorProfile.objects.filter(id__in=flat_friend_ids).select_related(
        "user"
    )

    context = {
        "can_follow_authors": can_follow_authors,
        "already_following_authors": already_following_authors,
        "denied_follow_authors": denied_follow_authors,
        "friends": friends,
    }
    return render(request, "friends_page.html", context)


@login_required
def follow_author_pyhn(request, author_id):
    """
    Handles sending and resending follow requests, as well as unfollowing authors.
    If the user unfollows an author who is also a friend, the friendship is removed.
    """
    if request.method == "POST":
        current_author = request.user.author_profile

        if current_author.id == author_id:
            messages.warning(request, "You cannot follow or unfollow yourself.")
            return redirect("friends_page")

        target_author = get_object_or_404(AuthorProfile, id=author_id)

        # Check if a follow relationship or request already exists
        existing_relation = Follower.objects.filter(
            user1=current_author, user2=target_author
        ).first()

        if existing_relation:
            if existing_relation.status == "P":
                messages.info(request, "A follow request is already pending.")
            elif existing_relation.status == "A":
                # Unfollow the author
                existing_relation.delete()

                # Remove friendship if it exists
                friendship = Friends.objects.filter(
                    Q(user1=current_author, user2=target_author)
                    | Q(user1=target_author, user2=current_author)
                ).first()

                if friendship:
                    friendship.delete()
                    messages.success(
                        request,
                        f"You have unfollowed and unfriended {target_author.user.username}.",
                    )
                else:
                    messages.success(
                        request, f"You have unfollowed {target_author.user.username}."
                    )

                # Optionally, you might want to delete the reciprocal follow if you want to completely sever the connection
                # Uncomment the following lines if needed:
                # reciprocal_relation = Follower.objects.filter(
                #     user1=target_author, user2=current_author
                # ).first()
                # if reciprocal_relation:
                #     reciprocal_relation.delete()

            elif existing_relation.status == "D":
                # Resend a follow request
                existing_relation.status = "P"
                existing_relation.created_at = datetime.now()
                existing_relation.save()
                messages.success(request, "Follow request has been re-sent.")
        else:
            # Create a new follow request
            Follower.objects.create(
                user1=current_author, user2=target_author, created_by=current_author
            )
            messages.success(request, "Follow request sent successfully.")

        return redirect("friends_page")
    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@login_required
def accept_follow_request_pyhn(request, request_id):
    """
    Accepts a pending follow request.
    If mutual following is detected, establishes a friendship.
    """
    if request.method == "POST":
        current_author = request.user.author_profile
        follow_request = get_object_or_404(
            Follower, id=request_id, user2=current_author, status="P"
        )

        # Accept the follow request
        follow_request.status = "A"
        follow_request.updated_at = datetime.now()
        follow_request.updated_by = current_author
        follow_request.save()

        messages.success(
            request,
            f"You have accepted the follow request from {follow_request.user1.user.username}.",
        )

        # Check for mutual following
        mutual_follow = Follower.objects.filter(
            user1=current_author, user2=follow_request.user1, status="A"
        ).exists()

        if mutual_follow:
            # Establish friendship
            try:
                # Ensure consistent ordering by user ID
                user1, user2 = (
                    (current_author, follow_request.user1)
                    if current_author.id < follow_request.user1.id
                    else (follow_request.user1, current_author)
                )

                # Create a single Friends instance
                Friends.objects.create(
                    user1=user1,
                    user2=user2,
                    created_by=current_author,  # Assuming 'created_by' refers to the initiator
                )
                messages.success(
                    request,
                    f"You are now friends with {follow_request.user1.user.username}.",
                )
            except IntegrityError:
                # Friendship already exists
                messages.info(
                    request,
                    f"You are already friends with {follow_request.user1.user.username}.",
                )
        return redirect("notifications")
    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@login_required
def deny_follow_request_pyhn(request, request_id):
    """
    Denies a pending follow request.
    """
    if request.method == "POST":
        current_author = request.user.author_profile
        follow_request = get_object_or_404(
            Follower, id=request_id, user2=current_author, status="P"
        )

        follow_request.status = "D"
        follow_request.updated_at = datetime.now()
        follow_request.updated_by = current_author
        follow_request.save()

        return redirect("notifications")
    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@login_required
def unfriend(request, friend_id):
    """
    Removes an existing friendship between the current user and another user.
    """
    if request.method == "POST":
        current_author = request.user.author_profile
        friend = get_object_or_404(AuthorProfile, id=friend_id)

        # Determine ordering based on user IDs to match Friends model constraints
        if current_author.id < friend.id:
            user1, user2 = current_author, friend
        else:
            user1, user2 = friend, current_author

        # Fetch the Friends instance
        friendship = Friends.objects.filter(user1=user1, user2=user2).first()

        if friendship:
            friendship.delete()
            messages.success(request, f"You have unfriended {friend.user.username}.")
        else:
            messages.info(request, "Friendship does not exist.")

        return redirect("friends_page")
    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")
