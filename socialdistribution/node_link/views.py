# Django imports
from rest_framework import viewsets
from django.shortcuts import render
from django.http import HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from .serializers import NodeSerializer, NotificationSerializer
from rest_framework.response import Response
from rest_framework.decorators import action

# Project imports
from node_link.models import Node, Notification
from authorApp.models import Friends, Follower
from postApp.models import Post
from node_link.utils.common import is_approved

# post edit/create methods


@is_approved
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
        following = list(
            Follower.objects.filter(Q(actor=user, status=True)).values_list(
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
            )
            .distinct()
            .order_by("-updated_at")
            .values_list("uuid", flat=True)
        )

        context = {"all_ids": all_posts}

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


class NodeViewSet(viewsets.ModelViewSet):
    """API endpoint for Node objects"""

    queryset = Node.objects.all()
    serializer_class = NodeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def active_nodes(self, request, pk=None):
        """List only active nodes"""
        active_nodes = Node.objects.filter(deleted_at__isnull=True)
        serializer = self.get_serializer(active_nodes, many=True)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    """API endpoint for Notification objects"""

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """List only unread notifications"""
        unread_notifications = Notification.objects.filter(
            user=request.user.author_profile, is_read=False
        )
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data)
