# Standard Library Imports
from datetime import datetime
from urllib.parse import unquote

# Django Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseNotAllowed, HttpResponseRedirect

# Rest Framework Imports
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    action,
)

# Third-Party Imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Project Imports
from .forms import EditProfileForm, SignUpForm, LoginForm
from .models import Friends, Follower, AuthorProfile
from .serializers import AuthorProfileSerializer, FollowerSerializer, FriendSerializer
from node_link.models import Node, Notification
from node_link.utils.common import CustomPaginator, has_access, is_approved
from node_link.utils.communication import send_to_remote_inboxes

from postApp.models import Post
from postApp.serializers import PostSerializer, LikeSerializer, CommentSerializer
from postApp.utils.fetch_github_activity import fetch_github_events
from authorApp.models import AuthorProfile, Friends, Follower
from authorApp.serializers import FollowerSerializer
import requests


# Create your views here.
# sign up
def signup_view(request):
    if request.user.is_authenticated and request.user.is_approved:
        return redirect("node_link:home", username=request.user.username)
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

            # Retrieve the first node in the Node table
            first_node = Node.objects.first()
            if not first_node:
                messages.error(request, "No nodes are available to assign.")
                return redirect("authorApp:signup")
            user.local_node = first_node
            user.user_serial = user.username

            user.save()

            # Create an AuthorProfile linked to the user and assign the first node
            AuthorProfile.objects.create(
                user=user,
                # Set other author-specific fields if necessary
            )

            user.backend = "django.contrib.auth.backends.ModelBackend"

            auth_login(request, user)
            return redirect("node_link:home", request.user.username)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_approved:
                auth_login(request, user)
                return redirect("node_link:home", username=user.username)
            else:
                messages.error(request, "Your account is not approved.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("authorApp:login")


@is_approved
def profile_display(request, author_un):
    if request.method == "GET":
        current_user = request.user.author_profile

        author = get_object_or_404(
            AuthorProfile,
            user__username=author_un,
        )
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
            if has_access(request, a.uuid, username=request.user.username):
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
    return redirect("node_link:home", request.user.username)


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
            new_follow = Follower.objects.create(
                actor=current_author, object=target_author, created_by=current_author
            )
            messages.success(request, "Follow create successfully.")

            if target_author.user.local_node.is_remote:
                # send follow request to remote
                follow_request_json = FollowerSerializer(
                    new_follow, context={"request": request}
                ).data

                send_to_remote_inboxes(follow_request_json, target_author)
                messages.success(request, "Follow request sent to remote successfully.")

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    else:
        return HttpResponseNotAllowed(["POST"], "Invalid request method.")


@is_approved
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


@is_approved
def explore_users(request):
    query = request.GET.get("q", "")  # Search query
    sort_by = request.GET.get("sort", "user__display_name")  # Sorting parameter
    direction = request.GET.get("direction", "asc")  # Sorting direction (asc/desc)

    current_author = request.user.author_profile

    exclude_id = [
        a.user2.id if a.user1 == current_author else a.user1.id
        for a in Friends.objects.filter(
            Q(user1=current_author) | Q(user2=current_author)
        )
    ] + [
        a.object.id
        for a in list(
            Follower.objects.filter(actor=current_author, status__in=["a", "p"])
        )
    ]
    all_authors = AuthorProfile.objects.exclude(id__in=exclude_id)

    # Filter by search query
    if query:
        all_authors = all_authors.filter(user__display_name__icontains=query)

    # Sorting logic

    if direction == "desc":
        sort_by = f"-{sort_by}"
        direction = "asc"
    else:
        direction = "desc"
    all_authors = all_authors.order_by(sort_by)

    context = {
        "authors": all_authors,
        "search_query": query,
        "sort_by": sort_by.lstrip("-"),
        "direction": direction,
    }
    return render(request, "explore_users.html", context)


# ViewSet for AuthorProfile API
class AuthorProfileViewSet(viewsets.ModelViewSet):

    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a list of all authors.",
        responses={
            200: openapi.Response(
                description="A list of authors.",
                schema=AuthorProfileSerializer(many=True),
                examples={
                    "application/json": {
                        "type": "authors",
                        "authors": [
                            {
                                "type": "author",
                                "id": "http://localhost:8000/api/authors/johndoe",
                                "host": "http://localhost:8000",
                                "displayName": "John Doe",
                                "github": "https://github.com/johndoe",
                                "profileImage": "http://example.com/images/johndoe.png",
                                "page": "http://localhost:8000/authors/johndoe/profile",
                            }
                        ],
                    }
                },
            )
        },
        tags=["Authors"],
    )
    def list(self, request, *args, **kwargs):
        authors = AuthorProfile.objects.all().order_by("id")
        if request.query_params:
            paginator = CustomPaginator()
            paginated_authors = paginator.paginate_queryset(authors, request)
            serializer = AuthorProfileSerializer(paginated_authors, many=True)
        else:
            serializer = AuthorProfileSerializer(authors, many=True)

        # Wrap the serialized data in the required format
        response_data = {"type": "authors", "authors": serializer.data}
        return Response(response_data)

    @swagger_auto_schema(
        operation_description="Retrieve an author's profile by username.",
        responses={
            200: openapi.Response(
                description="An author's profile.",
                schema=AuthorProfileSerializer(),
                examples={
                    "application/json": {
                        "type": "author",
                        "id": "http://localhost:8000/api/authors/johndoe",
                        "host": "http://localhost:8000",
                        "user": {
                            "username": "johndoe",
                            "first_name": "John",
                            "last_name": "Doe",
                            "email": "john@example.com",
                            "date_ob": "1990-01-01",
                            "display_name": "John Doe",
                            "profileImage": "http://example.com/images/johndoe.png",
                        },
                        "github": "https://github.com/johndoe",
                        "local_node": "http://localhost:8000",
                    }
                },
            ),
            404: openapi.Response(
                description="Author not found.",
                examples={"application/json": {"detail": "Author not found."}},
            ),
        },
        tags=["Authors"],
        manual_parameters=[
            openapi.Parameter(
                "username",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
    )

    # Retrieve a single author by username
    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        author = get_object_or_404(AuthorProfile, user__username=pk)
        serializer = AuthorProfileSerializer(author)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update a Author entirely.",
        request_body=AuthorProfileSerializer,
        responses={
            200: openapi.Response(
                description="Author updated successfully.",
                schema=AuthorProfileSerializer(),
                examples={
                    "application/json": {
                        "type": "author",
                        "id": "http://localhost:8000/api/authors/johndoe",
                        "host": "http://localhost:8000",
                        "user": {
                            "username": "johndoe",
                            "first_name": "John",
                            "last_name": "Doe",
                            "email": "john@example.com",
                            "date_ob": "1990-01-01",
                            "profileImage": "http://example.com/images/johndoe.png",
                        },
                        "github": "https://github.com/johndoe",
                        "local_node": "http://localhost:8000",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            404: "Not Found - Notification does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        manual_parameters=[
            openapi.Parameter(
                "username",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
        tags=["Authors"],
    )
    def update(self, request, *args, **kwargs):

        username = kwargs.get("pk")

        # Retrieve the author by username instead of id
        author = get_object_or_404(AuthorProfile, user__username=username)

        # Use the serializer to validate and update the data
        serializer = self.get_serializer(author, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
        )

    @swagger_auto_schema(
        operation_description="Retrieve followers of an author.",
        responses={
            200: openapi.Response(
                description="A list of followers.",
                schema=FollowerSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "actor": {
                                "type": "author",
                                "id": "http://localhost:8000/api/authors/janedoe",
                                "host": "http://localhost:8000",
                                "user": {
                                    "username": "janedoe",
                                    "first_name": "Jane",
                                    "last_name": "Doe",
                                    "email": "jane@example.com",
                                    "date_ob": "1992-05-15",
                                    "display_name": "John Doe",
                                    "profileImage": "http://example.com/images/janedoe.png",
                                },
                                "github": "https://github.com/janedoe",
                                "local_node": "http://localhost:8000",
                            },
                            "object": "author data",
                            "status": "approved",
                        },
                    ]
                },
            ),
            404: openapi.Response(
                description="Author not found.",
                examples={"application/json": {"detail": "Author not found."}},
            ),
        },
        tags=["Followers"],
        manual_parameters=[
            openapi.Parameter(
                "username",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
    )
    # Custom action to list followers of an author
    @action(detail=True, methods=["get"])
    def followers(self, request, pk=None):
        # Get the author by username or pk
        author = get_object_or_404(AuthorProfile, user__username=pk)
        # Filter followers where this author is the 'object'
        followers = Follower.objects.filter(object=author)
        # Serialize the data
        serializer = FollowerSerializer(followers, many=True)
        # Structure the response to match the required format
        response_data = {"type": "followers", "followers": serializer.data}
        return Response(response_data)

    @swagger_auto_schema(
        auto_schema=None,
        operation_description="Retrieve friends of an author.",
        responses={
            200: openapi.Response(
                description="A list of friends.",
                schema=FriendSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "user1": "author data",
                            "user2": "friend data",
                            "status": True,
                        },
                    ]
                },
            ),
            404: openapi.Response(
                description="Author not found.",
                examples={"application/json": {"detail": "Author not found."}},
            ),
        },
        tags=["Friends"],
        manual_parameters=[
            openapi.Parameter(
                "username",
                openapi.IN_PATH,
                description="Username of the author.",
                type=openapi.TYPE_STRING,
                required=True,
                example="johndoe",
            ),
        ],
    )
    # Custom action to list friends of an author
    @action(detail=True, methods=["get"])
    def friends(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        friends = Friends.objects.filter((Q(user1=author) | Q(user2=author)))
        serializer = FriendSerializer(friends, many=True)
        return Response(serializer.data)


class FollowersFQIDViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        methods=["get"],
        operation_summary="Retrieve follower relationship",
        operation_description=(
            "Retrieve the relationship between a local author and a foreign author identified by their FQID."
        ),
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Username of the local author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "follower_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the foreign author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Successful retrieval of follower relationship.",
                schema=FollowerSerializer(),
            ),
            404: openapi.Response(description="Follower not found."),
        },
        tags=["Followers"],
    )
    @swagger_auto_schema(
        methods=["put"],
        operation_summary="Add a follower",
        operation_description="Add a foreign author as a follower of a local author.",
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Username of the local author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "follower_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the foreign author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            201: openapi.Response(
                description="Follower successfully added.",
                examples={"application/json": {"detail": "Follower added."}},
            ),
            400: openapi.Response(
                description="Bad request (e.g., follower already exists).",
                examples={"application/json": {"detail": "Follower already exists."}},
            ),
        },
        tags=["Followers"],
    )
    @swagger_auto_schema(
        methods=["delete"],
        operation_summary="Remove a follower",
        operation_description="Remove a foreign author as a follower of a local author.",
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Username of the local author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "follower_fqid",
                openapi.IN_PATH,
                description="Fully Qualified ID (FQID) of the foreign author.",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            204: openapi.Response(
                description="Follower successfully removed.",
                examples={"application/json": {"detail": "Follower removed."}},
            ),
            404: openapi.Response(
                description="Follower not found.",
                examples={"application/json": {"detail": "Follower does not exist."}},
            ),
        },
        tags=["Followers"],
    )
    @action(
        detail=True,
        methods=["get", "put", "delete"],
        url_path="followers/(?P<follower_fqid>.+)",
    )
    def manage_follower(self, request, pk=None, follower_fqid=None):
        # Decode the foreign author FQID
        follower_fqid = unquote(follower_fqid)
        fqid_parts = follower_fqid.split("/")
        foreign_username = fqid_parts[len(fqid_parts) - 1]
        # Fetch the local author
        local_author = get_object_or_404(AuthorProfile, user__username=pk)

        # Check if the follower is already in the follower list
        try:
            foreign_author = get_object_or_404(
                AuthorProfile, user__username=foreign_username
            )
            follower_relationship = Follower.objects.get(
                actor=foreign_author, object=local_author
            )
        except (AuthorProfile.DoesNotExist, Follower.DoesNotExist):
            follower_relationship = None

        if request.method == "GET":
            # Check if FOREIGN_AUTHOR_FQID is a follower of AUTHOR_SERIAL
            if follower_relationship:
                serializer = FollowerSerializer(follower_relationship)
                return Response(serializer.data)
            return Response(status=status.HTTP_404_NOT_FOUND)

        elif request.method == "PUT":
            # Add FOREIGN_AUTHOR_FQID as a follower of AUTHOR_SERIAL
            if not follower_relationship:
                Follower.objects.create(
                    actor=foreign_author,
                    object=local_author,
                    status="a",
                    created_by=foreign_author,
                )
                return Response(
                    {"detail": "Follower added."}, status=status.HTTP_201_CREATED
                )
            return Response(
                {"detail": "Follower already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        elif request.method == "DELETE":
            # Remove FOREIGN_AUTHOR_FQID as a follower of AUTHOR_SERIAL
            if follower_relationship:
                follower_relationship.delete()
                return Response(
                    {"detail": "Follower removed."}, status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {"detail": "Follower does not exist."}, status=status.HTTP_404_NOT_FOUND
            )


class SingleAuthorView(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve Author by Fully Qualified ID (FQID)",
        operation_description=(
            "Fetch detailed information about an author using their Fully Qualified ID (FQID). "
            "The FQID typically follows the format `<host>/api/authors/<username>`."
        ),
        responses={
            200: openapi.Response(
                description="Successfully retrieved author details.",
                examples={
                    "application/json": {
                        "id": "http://example.com/api/authors/username",
                        "host": "http://example.com/",
                        "type": "author",
                        "displayName": "Author Display Name",
                        "github": "https://github.com/username",
                        "profileImage": "http://example.com/media/profile.jpg",
                        "page": "http://example.com/authors/username",
                    }
                },
            ),
            404: openapi.Response(
                description="Author not found.",
                examples={"application/json": {"detail": "Not found."}},
            ),
        },
        manual_parameters=[
            openapi.Parameter(
                name="author_fqid",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                description=(
                    "Fully Qualified ID of the author. It should be in the format "
                    "`<host>/api/authors/<username>`."
                ),
                required=True,
            )
        ],
    )
    def get(self, request, author_fqid):
        """
        GET: Retrieve a single author using its FQID.
        """
        author_fqid = unquote(author_fqid)
        fqid_parts = author_fqid.split("/")
        author_username = fqid_parts[len(fqid_parts) - 1]

        author = get_object_or_404(AuthorProfile, user__username=author_username)
        serializer = AuthorProfileSerializer(author)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([BasicAuthentication])
def author_inbox_view(request, author_serial):
    """
    Handles incoming activities directed to a specific author's inbox

    Supported types: "post", "like", "comment", "follow"
    """
    # retrieve the author
    print("Incoming data:", request.data)

    # get the nodes that we have locally
    # check the request for the id of the node and check if it is active
    # if not active return resposne to them saying they don't have access

    try:
        author = AuthorProfile.objects.get(user__username=author_serial)
    except AuthorProfile.DoesNotExist:
        return Response({"error": "Author not found"}, status=404)

    # retrieve the activity
    data = request.data
    object_type = data.get("type")

    # filter base on type
    if object_type == "post":
        serializer = PostSerializer(data=data, context={"author": author})
    elif object_type == "like":
        serializer = LikeSerializer(data=data, context={"author": author})
    elif object_type == "comment":
        serializer = CommentSerializer(data=data, context={"author": author})
    elif object_type == " follow":
        serializer = FollowerSerializer(data=data, context={"author": author})
    else:
        return Response(
            {"error": "Unsupported object type"}, status=status.HTTP_400_BAD_REQUEST
        )

    # save the object to our database
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "sucessful"}, status=status.HTTP_201_CREATED)
