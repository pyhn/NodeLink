from rest_framework import serializers
from authorApp.models import AuthorProfile
from node_link.models import Node, Notification


class AuthorsSerializer(serializers.ModelSerializer):
    """Serializer for author profiles, including related fields."""

    type = serializers.CharField(default="author")
    id = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()

    class Meta:
        model = AuthorProfile
        fields = [
            "type",
            "id",
            "host",
            "display_name",
            "github",
            "profileImage",
        ]

    def get_id(self, obj):
        # Construct the API URL for the author
        return f"{obj.local_node.url}/api/authors/{obj.user.username}"

    def get_host(self, obj):
        return obj.local_node.url


class FollowRequestSerializer(serializers.ModelSerializer):
    """Serializer for follow requests between authors."""

    type = serializers.CharField(default="follow")
    summary = serializers.CharField()

    class Meta:
        model = AuthorProfile  # Replace with your FollowRequest model if available
        fields = [
            "type",
            "summary",
            "actor",
            "object",
        ]


class NodeSerializer(serializers.ModelSerializer):
    """Serializer for Node data."""

    class Meta:
        model = Node
        fields = ['url', 'created_at', 'created_by', 'updated_at', 'deleted_at', 'deleted_by']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification data."""

    class Meta:
        model = Notification
        fields = [
            'user',
            'message',
            'created_at',
            'is_read',
            'notification_type',
            'related_object_id',
            'author_picture_url',
            'follow_request_message',
            'link_url'
        ]
