# Django Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from .forms import EditProfileForm
from .serializers import AuthorProfileSerializer, FollowerSerializer, FriendSerializer
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import action
from django.db import IntegrityError
from django.http import HttpResponseNotAllowed, HttpResponseRedirect

# Project Imports
from .models import (
    Friends,
    Follower,
    AuthorProfile,
)
from node_link.models import Node
from .forms import SignUpForm, LoginForm
from node_link.utils.common import has_access, is_approved
from postApp.models import Post

# Third Party Imports
from datetime import datetime

# Create your views here.
# sign up
def signup_view(request):
    if request.user.is_authenticated and request.user.is_approved:
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
    if request.user.is_authenticated and request.user.is_approved:
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


@is_approved
def profile_display(request, author_un):
    if request.method == "GET":
        current_user = request.user.author_profile
        author = get_object_or_404(AuthorProfile, user__username=author_un)
        all_ids = list(Post.objects.filter(author=author).order_by("-created_at"))

        # Determine the button to display
        is_friend = Friends.objects.filter(
            Q(user1=current_user, user2=author) | Q(user1=author, user2=current_user)
        ).exists()

        follow_status = Follower.objects.filter(
            actor=current_user, object=author
        ).first()

        requested_by_author = Follower.objects.filter(
            actor=author, object=current_user, status="p"
        ).exists()
        ff_request = ""
        if is_friend:
            button_type = "unfriend"
            ff_request = Friends.objects.filter(
                Q(user1=current_user, user2=author)
                | Q(user1=author, user2=current_user)
            ).first()
        elif follow_status and follow_status.status == "a" and requested_by_author:
            button_type = "unfollow/accept_or_deny"
            ff_request = Follower.objects.filter(
                actor=author, object=current_user, status="p"
            ).first()
        elif follow_status and follow_status.status == "a":
            button_type = "unfollow"
            ff_request = follow_status
        elif requested_by_author:
            button_type = "accept_or_deny"
            ff_request = Follower.objects.filter(
                actor=author, object=current_user, status="p"
            ).first()
        elif follow_status and follow_status.status == "p":
            button_type = "pending"
            ff_request = follow_status

        else:
            button_type = "follow"

        filtered_ids = []
        for a in all_ids:
            if has_access(request, a.uuid):
                filtered_ids.append(a)

        context = {
            "all_ids": filtered_ids,
            "author": author,
            "button_type": button_type,
            "ff_request": ff_request,
            "num_following": Follower.objects.filter(actor=author).count(),
            "num_friends": Friends.objects.filter(
                Q(user1=author) | Q(user2=author)
            ).count(),
            "num_followers": Follower.objects.filter(object=author).count(),
        }
        return render(request, "user_profile.html", context)
    return redirect("node_link:home")


@is_approved
def friends_page(request):
    """
    Renders a page listing all authors with a 'Follow' button next to each.
    Separates authors into those you can follow, those you are already following,
    and those who are your friends.
    """
    current_author = request.user.author_profile
    # Get a list of author IDs that the current user is already following (status='A')
    following = [
        a.object
        for a in list(Follower.objects.filter(actor=current_author, status="a"))
    ]
    followers = [
        a.actor
        for a in list(Follower.objects.filter(object=current_author, status="a"))
    ]

    # Get a list of author IDs that the current user has pending follow requests with (status='P')
    pending_request = [
        a.object
        for a in list(Follower.objects.filter(actor=current_author, status="p"))
    ]

    # Get a list of author IDs that have denied follow requests (status='D')
    denied_request = [
        a.object
        for a in list(Follower.objects.filter(actor=current_author, status="d"))
    ]

    # Get a list of author IDs that have requested to follow
    requested = [
        (a.actor, a.id)
        for a in list(Follower.objects.filter(object=current_author, status="p"))
    ]

    # Get a list of friend IDs
    friend = [
        a.user2 if a.user1 == current_author else a.user1
        for a in Friends.objects.filter(
            Q(user1=current_author) | Q(user2=current_author)
        )
    ]

    exclude_id = [a.id for a in (friend + following + pending_request)]
    following = list(following)
    followers = list(followers)

    # Authors the user can follow (not already following, no pending requests, and not already friends)
    can_follow_authors = AuthorProfile.objects.exclude(id__in=exclude_id)

    context = {
        "can_follow_authors": can_follow_authors,
        "pending_authors": pending_request,
        "requested_authors": requested,
        "already_following_authors": following,
        "denied_follow_authors": denied_request,
        "friends": friend,
        "followers": followers,
    }
    return render(request, "friends_page.html", context)


@is_approved
def accept_follow_request(request, request_id):
    """
    Accepts a pending follow request.
    If mutual following is detected, establishes a friendship.
    """
    if request.method == "POST":
        current_author = request.user.author_profile
        follow_request = get_object_or_404(
            Follower, id=request_id, object=current_author, status="p"
        )

        # Accept the follow request
        follow_request.status = "a"
        follow_request.updated_at = datetime.now()
        follow_request.updated_by = current_author
        follow_request.save()

        messages.success(
            request,
            f"You have accepted the follow request from {follow_request.actor.user.username}.",
        )

        # Check for mutual following
        mutual_follow = Follower.objects.filter(
            actor=current_author, object=follow_request.actor, status="a"
        ).exists()

        if mutual_follow:
            # Establish friendship
            try:
                # Ensure consistent ordering by user ID
                user1, user2 = (
                    (current_author, follow_request.actor)
                    if current_author.id < follow_request.actor.id
                    else (follow_request.actor, current_author)
                )

                # Create a single Friends instance
                Friends.objects.create(
                    user1=user1,
                    user2=user2,
                    created_by=current_author,  # Assuming 'created_by' refers to the initiator
                )
                messages.success(
                    request,
                    f"You are now friends with {follow_request.actor.user.username}.",
                )
            except IntegrityError:
                # Friendship already exists
                messages.info(
                    request,
                    f"You are already friends with {follow_request.actor.user.username}.",
                )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@is_approved
def deny_follow_request(request, request_id):
    """
    Denies a pending follow request.
    """
    if request.method == "POST":
        current_author = request.user.author_profile
        follow_request = get_object_or_404(
            Follower, id=request_id, object=current_author, status="p"
        )

        follow_request.status = "d"
        follow_request.updated_at = datetime.now()
        follow_request.updated_by = current_author
        follow_request.save()

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@is_approved
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
        friendship = Friends.objects.filter(
            Q(user1=user1, user2=user2) | Q(user1=user2, user2=user1)
        ).first()
        following = Follower.objects.filter(
            actor=current_author, object=friend_id
        ).first()

        if friendship:

            following.delete()

            friendship.delete()
            messages.success(request, f"You have unfriended {friend.user.username}.")
        else:
            messages.info(request, "Friendship does not exist.")

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@is_approved
def follow_author(request, author_id):
    """
    Handles sending and resending follow requests, as well as unfollowing authors.
    If the user unfollows an author who is also a friend, the friendship is removed.
    """
    if request.method == "POST":
        current_author = request.user.author_profile

        if (
            current_author.id == author_id
        ):  #!!! PART 3 NOTE: the ID is not longer unique for multiple nodes
            messages.warning(request, "You cannot follow or unfollow yourself.")
            return redirect("authorApp:friends_page")

        target_author = get_object_or_404(AuthorProfile, id=author_id)

        # Check if a follow relationship or request already exists
        existing_relation = Follower.objects.filter(
            actor=current_author, object=target_author
        ).first()

        if existing_relation:
            if existing_relation.status == "p":
                messages.info(request, "A follow request is already pending.")
            elif existing_relation.status == "a":
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

            elif existing_relation.status == "d":
                # Resend a follow request
                existing_relation.status = "p"
                existing_relation.created_at = datetime.now()
                existing_relation.save()
                messages.success(request, "Follow request has been re-sent.")
        else:
            # Create a new follow request
            Follower.objects.create(
                actor=current_author, object=target_author, created_by=current_author
            )
            messages.success(request, "Follow request sent successfully.")

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(
                "authorApp:profile_display", author_un=request.user.username
            )
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, "authorApp/edit_profile.html", {"form": form})


# ViewSet for AuthorProfile API
class AuthorProfileViewSet(viewsets.ViewSet):
    # Retrieve all authors
    def list(self, request):
        authors = AuthorProfile.objects.all()
        serializer = AuthorProfileSerializer(authors, many=True)
        return Response(serializer.data)

    # Retrieve a single author by username
    def retrieve(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        serializer = AuthorProfileSerializer(author)
        return Response(serializer.data)

    # Custom action to list followers of an author
    @action(detail=True, methods=["get"])
    def followers(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        followers = Follower.objects.filter(object=author)
        serializer = FollowerSerializer(followers, many=True)
        return Response(serializer.data)

    # Custom action to list friends of an author
    @action(detail=True, methods=["get"])
    def friends(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        friends = Friends.objects.filter((Q(user1=author) | Q(user2=author)))
        serializer = FriendSerializer(friends, many=True)
        return Response(serializer.data)
