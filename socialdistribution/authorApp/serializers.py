from rest_framework import serializers
from authorApp.models import AuthorProfile, Follower, Friends, User
from django.urls import reverse

# Serializer for User data
class UserSerializer(serializers.ModelSerializer):
    """Serializer for User details"""

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "date_ob",
            "profileImage",
        ]


# Serializer for AuthorProfile data
class AuthorProfileSerializer(serializers.ModelSerializer):
    """Serializer for AuthorProfile, includes associated User data"""

    id = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    type = serializers.CharField(default="author")
    displayName = serializers.SerializerMethodField()
    github = serializers.SerializerMethodField()
    profileImage = serializers.SerializerMethodField()
    page = serializers.SerializerMethodField()

    class Meta:
        model = AuthorProfile
        fields = ["type", "id", "host", "displayName", "github", "profileImage", "page"]

    def get_id(self, obj):
        # Construct the API URL using the local node and username
        return f"{obj.local_node.url}/api/authors/{obj.user.username}"

    def get_host(self, obj):
        return obj.local_node.url

    def get_displayName(self, obj):
        return obj.user.display_name

    def get_github(self, obj):
        return obj.github

    def get_profileImage(self, obj):
        return str(obj.user.profileImage)

    def get_page(self, obj):
        return str(
            obj.local_node.url.rstrip("/")
            + reverse("authorApp:profile_display", args=[obj.user.username])
        )


# Serializer for followers
class FollowerSerializer(serializers.ModelSerializer):
    """Serializer for followers"""

    actor = AuthorProfileSerializer(read_only=True)
    object = AuthorProfileSerializer(read_only=True)

    class Meta:
        model = Follower
        fields = ["actor", "object", "status"]


# Serializer for friendships
class FriendSerializer(serializers.ModelSerializer):
    """Serializer for friendships"""

    user1 = AuthorProfileSerializer(read_only=True)
    user2 = AuthorProfileSerializer(read_only=True)

    class Meta:
        model = Friends
        fields = ["user1", "user2"]
