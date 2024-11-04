# Django imports
from rest_framework import viewsets
from django.shortcuts import render
from django.http import HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from .serializers import NodeSerializer, NotificationSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Project imports
from node_link.models import Node, Notification
from authorApp.models import Friends, Follower
from postApp.models import Post
from node_link.utils.common import is_approved

# post edit/create methods


@is_approved
def home(request, username):

    if request.method == "GET":
        template_name = "home.html"
        user = request.user.author_profile

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

    @swagger_auto_schema(
        operation_description="Retrieve a list of all nodes.",
        responses={
            200: openapi.Response(
                description="A list of nodes.",
                schema=NodeSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "name": "Node 1",
                            "host": "http://node1.example.com",
                            "deleted_at": None,
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    def list(self, request, *args, **kwargs):
        """
        Retrieve a list of all nodes.

        **Usage:**
        - **Method:** GET
        - **URL:** `/api/nodes/`
        - **Authentication:** Required

        **Response Fields:**
        - **id (integer):** Unique identifier of the node.
        - **name (string):** Name of the node.
        - **host (string):** Host URL of the node.
        - **deleted_at (datetime or null):** Deletion timestamp, null if active.
        - **... other fields ...**

        **Examples:**
        ```json
        [
            {
                "id": 1,
                "name": "Node 1",
                "host": "http://node1.example.com",
                "deleted_at": null,
                // ... other fields ...
            },
            // More nodes...
        ]
        ```
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new node.",
        request_body=NodeSerializer,
        responses={
            201: openapi.Response(
                description="Node created successfully.",
                schema=NodeSerializer(),
                examples={
                    "application/json": {
                        "id": 2,
                        "name": "Node 2",
                        "host": "http://node2.example.com",
                        "deleted_at": "null",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new node.

        **Usage:**
        - **Method:** POST
        - **URL:** `/api/nodes/`
        - **Authentication:** Required
        - **Request Body:** Node data in JSON format.

        **Request Fields:**
        - **name (string, required):** Name of the node.
        - **host (string, required):** Host URL of the node.
        - **... other fields ...**

        **Response Fields:**
        - Same as the request fields, plus:
        - **id (integer):** Unique identifier of the node.

        **Examples:**

        **Request Body:**
        ```json
        {
            "name": "Node 2",
            "host": "http://node2.example.com",
            // ... other fields ...
        }
        ```

        **Response:**
        ```json
        {
            "id": 2,
            "name": "Node 2",
            "host": "http://node2.example.com",
            "deleted_at": null,
            // ... other fields ...
        }
        ```
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific node by ID.",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the node.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Node retrieved successfully.",
                schema=NodeSerializer(),
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Node 1",
                        "host": "http://node1.example.com",
                        "deleted_at": "null",
                    }
                },
            ),
            404: "Not Found - Node does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific node by ID.

        **Usage:**
        - **Method:** GET
        - **URL:** `/api/nodes/{id}/`
        - **Authentication:** Required
        - **Path Parameters:**
            - **id (integer):** ID of the node.

        **Response Fields:**
        - Same as in the list method.

        **Examples:**
        ```json
        GET /api/nodes/1/

        Response:
        {
            "id": 1,
            "name": "Node 1",
            "host": "http://node1.example.com",
            "deleted_at": null,
            // ... other fields ...
        }
        ```
        """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a node entirely.",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the node.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        request_body=NodeSerializer,
        responses={
            200: openapi.Response(
                description="Node updated successfully.",
                schema=NodeSerializer(),
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Updated Node Name",
                        "host": "http://updatednode.example.com",
                        "deleted_at": "null",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            404: "Not Found - Node does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    def update(self, request, *args, **kwargs):
        """
        Update a node entirely.

        **Usage:**
        - **Method:** PUT
        - **URL:** `/api/nodes/{id}/`
        - **Authentication:** Required
        - **Path Parameters:**
            - **id (integer):** ID of the node.
        - **Request Body:** Complete node data in JSON format.

        **Examples:**
        ```json
        PUT /api/nodes/1/

        Request Body:
        {
            "name": "Updated Node Name",
            "host": "http://updatednode.example.com",
            // ... other fields ...
        }

        Response:
        {
            "id": 1,
            "name": "Updated Node Name",
            "host": "http://updatednode.example.com",
            "deleted_at": null,
            // ... other fields ...
        }
        ```
        """
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a node.",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the node.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        request_body=NodeSerializer,
        responses={
            200: openapi.Response(
                description="Node partially updated successfully.",
                schema=NodeSerializer(),
                examples={
                    "application/json": {
                        "id": 1,
                        "name": "Partially Updated Node Name",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            404: "Not Found - Node does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a node.

        **Usage:**
        - **Method:** PATCH
        - **URL:** `/api/nodes/{id}/`
        - **Authentication:** Required
        - **Path Parameters:**
            - **id (integer):** ID of the node.
        - **Request Body:** Partial node data in JSON format.

        **Examples:**
        ```json
        PATCH /api/nodes/1/

        Request Body:
        {
            "name": "Partially Updated Node Name"
        }

        Response:
        {
            "id": 1,
            "name": "Partially Updated Node Name",
            "host": "http://node1.example.com",
            "deleted_at": null,
            // ... other fields ...
        }
        ```
        """
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a node.",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the node.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        responses={
            204: "No Content - Node deleted successfully.",
            404: "Not Found - Node does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete a node.

        **Usage:**
        - **Method:** DELETE
        - **URL:** `/api/nodes/{id}/`
        - **Authentication:** Required
        - **Path Parameters:**
            - **id (integer):** ID of the node.

        **Examples:**
        ```json
        DELETE /api/nodes/1/

        Response:
        Status Code: 204 No Content
        ```
        """
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a list of active nodes.",
        responses={
            200: openapi.Response(
                description="A list of active nodes.",
                schema=NodeSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "name": "Active Node 1",
                            "host": "http://activenode1.example.com",
                            "deleted_at": "null",
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Nodes"],
    )
    @action(detail=False, methods=["get"])

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

    @swagger_auto_schema(
        operation_description="Retrieve a list of notifications.",
        responses={
            200: openapi.Response(
                description="List of notifications retrieved successfully.",
                schema=NotificationSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "user": {
                                "id": 5,
                                "username": "johndoe",
                            },
                            "message": "You have a new follower.",
                            "is_read": False,
                            "created_at": "2024-11-02T18:00:00Z",
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Notifications"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new notification.",
        request_body=NotificationSerializer,
        responses={
            201: openapi.Response(
                description="Notification created successfully.",
                schema=NotificationSerializer(),
                examples={
                    "application/json": {
                        "id": 2,
                        "user": {
                            "id": 5,
                            "username": "johndoe",
                        },
                        "message": "Your post was liked.",
                        "is_read": False,
                        "created_at": "2024-11-02T19:00:00Z",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Notifications"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific notification by ID.",
        responses={
            200: openapi.Response(
                description="Notification retrieved successfully.",
                schema=NotificationSerializer(),
                examples={
                    "application/json": {
                        "id": 1,
                        "user": {
                            "id": 5,
                            "username": "johndoe",
                        },
                        "message": "You have a new follower.",
                        "is_read": False,
                        "created_at": "2024-11-02T18:00:00Z",
                    }
                },
            ),
            404: "Not Found - Notification does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the notification.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        tags=["Notifications"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a notification entirely.",
        request_body=NotificationSerializer,
        responses={
            200: openapi.Response(
                description="Notification updated successfully.",
                schema=NotificationSerializer(),
                examples={
                    "application/json": {
                        "id": 1,
                        "user": {
                            "id": 5,
                            "username": "johndoe",
                        },
                        "message": "Updated notification message.",
                        "is_read": True,
                        "created_at": "2024-11-02T18:00:00Z",
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            404: "Not Found - Notification does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the notification.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        tags=["Notifications"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a notification.",
        request_body=NotificationSerializer,
        responses={
            200: openapi.Response(
                description="Notification partially updated successfully.",
                schema=NotificationSerializer(),
                examples={
                    "application/json": {
                        "id": 1,
                        "is_read": True,
                    }
                },
            ),
            400: "Bad Request - Invalid data.",
            404: "Not Found - Notification does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the notification.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        tags=["Notifications"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a notification.",
        responses={
            204: "No Content - Notification deleted successfully.",
            404: "Not Found - Notification does not exist.",
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID of the notification.",
                type=openapi.TYPE_INTEGER,
                required=True,
                example=1,
            ),
        ],
        tags=["Notifications"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="List only unread notifications for the authenticated user.",
        responses={
            200: openapi.Response(
                description="List of unread notifications retrieved successfully.",
                schema=NotificationSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 3,
                            "user": {
                                "id": 5,
                                "username": "johndoe",
                            },
                            "message": "Someone commented on your post.",
                            "is_read": False,
                            "created_at": "2024-11-02T20:00:00Z",
                        },
                    ]
                },
            ),
            401: "Unauthorized - Authentication credentials were not provided or are invalid.",
        },
        tags=["Notifications"],
    )

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """List only unread notifications"""
        unread_notifications = Notification.objects.filter(
            user=request.user.author_profile, is_read=False
        )
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data)
