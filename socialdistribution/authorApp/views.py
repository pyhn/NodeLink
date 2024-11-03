# Django Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from .serializers import AuthorProfileSerializer, FollowerSerializer, FriendSerializer
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from authorApp.models import AuthorProfile


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


# ViewSet for AuthorProfile API
class AuthorProfileViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        operation_description="Retrieve a list of all authors.",
        responses={
            200: openapi.Response(
                description="A list of authors.",
                schema=AuthorProfileSerializer(many=True),
                examples={
                    'application/json': [
                        {
                            "type": "author",
                            "id": "http://localhost:8000/api/authors/johndoe",
                            "host": "http://localhost:8000",
                            "user": {
                                "username": "johndoe",
                                "first_name": "John",
                                "last_name": "Doe",
                                "email": "john@example.com",
                                "date_ob": "1990-01-01",
                                "profileImage": "http://example.com/images/johndoe.png"
                            },
                            "github": "https://github.com/johndoe",
                            "local_node": "http://localhost:8000"
                        },
                    ]
                }
            )
        },
        tags=['Authors'],
    )
    # Retrieve all authors
    def list(self, request):
        authors = AuthorProfile.objects.all()
        serializer = AuthorProfileSerializer(authors, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
    operation_description="Retrieve an author's profile by username.",
    responses={
        200: openapi.Response(
            description="An author's profile.",
            schema=AuthorProfileSerializer(),
            examples={
                'application/json': {
                    "type": "author",
                    "id": "http://localhost:8000/api/authors/johndoe",
                    "host": "http://localhost:8000",
                    "user": {
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "john@example.com",
                        "date_ob": "1990-01-01",
                        "profileImage": "http://example.com/images/johndoe.png"
                    },
                    "github": "https://github.com/johndoe",
                    "local_node": "http://localhost:8000"
                }
            }
        ),
        404: openapi.Response(
            description="Author not found.",
            examples={
                'application/json': {
                    "detail": "Author not found."
                }
            }
        ),
    },
    tags=['Authors'],
    manual_parameters=[
        openapi.Parameter(
            'username', openapi.IN_PATH,
            description="Username of the author.",
            type=openapi.TYPE_STRING,
            required=True,
            example="johndoe"
        ),
    ],
)
    # Retrieve a single author by username
    def retrieve(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        serializer = AuthorProfileSerializer(author)
        return Response(serializer.data)

    
    @swagger_auto_schema(
    operation_description="Retrieve followers of an author.",
    responses={
        200: openapi.Response(
            description="A list of followers.",
            schema=FollowerSerializer(many=True),
            examples={
                'application/json': [
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
                                "profileImage": "http://example.com/images/janedoe.png"
                            },
                            "github": "https://github.com/janedoe",
                            "local_node": "http://localhost:8000"
                        },
                        "object": "author data",
                        "status": "approved"
                    },
                ]
            }
        ),
        404: openapi.Response(
            description="Author not found.",
            examples={
                'application/json': {
                    "detail": "Author not found."
                }
            }
        ),
    },
    tags=['Followers'],
    manual_parameters=[
        openapi.Parameter(
            'username', openapi.IN_PATH,
            description="Username of the author.",
            type=openapi.TYPE_STRING,
            required=True,
            example="johndoe"
        ),
    ],
)
    # Custom action to list followers of an author
    @action(detail=True, methods=['get'])
    def followers(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        followers = Follower.objects.filter(object=author)
        serializer = FollowerSerializer(followers, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
    operation_description="Retrieve friends of an author.",
    responses={
        200: openapi.Response(
            description="A list of friends.",
            schema=FriendSerializer(many=True),
            examples={
                'application/json': [
                    {
                        "user1":  "author data",
                        "user2": "friend data",
                        "status": True
                    },
                ]
            }
        ),
        404: openapi.Response(
            description="Author not found.",
            examples={
                'application/json': {
                    "detail": "Author not found."
                }
            }
        ),
    },
    tags=['Friends'],
    manual_parameters=[
        openapi.Parameter(
            'username', openapi.IN_PATH,
            description="Username of the author.",
            type=openapi.TYPE_STRING,
            required=True,
            example="johndoe"
        ),
    ],
)
    # Custom action to list friends of an author
    @action(detail=True, methods=['get'])
    def friends(self, request, pk=None):
        author = get_object_or_404(AuthorProfile, user__username=pk)
        friends = Friends.objects.filter(
            (Q(user1=author) | Q(user2=author)) & Q(status=True)
        )
        serializer = FriendSerializer(friends, many=True)
        return Response(serializer.data)