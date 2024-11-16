# Django imports
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from django.shortcuts import render
from django.http import HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BasicAuthentication
from postApp.serializers import PostSerializer, LikeSerializer, CommentSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Project imports
from node_link.models import Node, Notification
from authorApp.models import Friends, Follower, AuthorProfile
from postApp.models import Post
from node_link.utils.common import is_approved

from postApp.utils.fetch_github_activity import fetch_github_events

# post edit/create methods


@is_approved
def home(request, username):

    if request.method == "GET":
        template_name = "home.html"
        user = request.user.author_profile

        github_activity = fetch_github_events(request)

        friends = list(
            Friends.objects.filter(Q(user1=user) | Q(user2=user)).values_list(
                "user1", "user2"
            )
        )
        friends = list(set(u_id for tup in friends for u_id in tup))
        following = list(
            Follower.objects.filter(Q(actor=user, status="a")).values_list(
                "object", flat=True
            )
        )

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
                | Q(author_id=user.id) & ~Q(visibility="d")
            )
            .distinct()
            .order_by("-updated_at")
            .values_list("uuid", flat=True)
        )

        context = {"all_ids": all_posts, "github_activity": github_activity}

        # Return the rendered template
        return render(request, template_name, context)
    return HttpResponseNotAllowed("Invalid Method;go home")


@is_approved
def notifications_view(request):
    notifications = Notification.objects.filter(
        user=request.user.author_profile
    ).order_by("-created_at")
    notifications.update(is_read=True)  # Mark notifications as read
    return render(request, "notifications.html", {"notifications": notifications})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([BasicAuthentication])
def author_inbox_view(request, author_serial):
    """
    Handles incoming activities directed to a specific author's inbox

    Supported types: "post", "like", "comment", "follow"
    """
    # retrieve the author
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
        # look at which one to use
        pass
    else:
        return Response(
            {"error": "Unsupported object type"}, status=status.HTTP_400_BAD_REQUEST
        )

    # save the object to our database
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "sucessful"}, status=status.HTTP_201_CREATED)
