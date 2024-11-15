from rest_framework import serializers
from authorApp.models import AuthorProfile, Follower, Friends, User

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

    user = UserSerializer(read_only=True)
    id = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    type = serializers.CharField(default="author")

    class Meta:
        model = AuthorProfile
        fields = ["type", "id", "host", "user", "github", "local_node"]

    def get_id(self, obj):
        # Construct the API URL using the local node and username
        return f"{obj.local_node.url}/api/authors/{obj.user.username}"

    def get_host(self, obj):
        return obj.local_node.url


class FollowerSerializer(serializers.ModelSerializer):
    """Custom Serializer for followers to match the required output format"""

    type = serializers.CharField(default="author", read_only=True)
    id = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    displayName = serializers.CharField(
        source="actor.user.display_name", read_only=True
    )
    page = serializers.SerializerMethodField()
    github = serializers.CharField(source="actor.github", read_only=True)
    profileImage = serializers.CharField(
        source="actor.user.profileImage.url", read_only=True
    )

    class Meta:
        model = Follower
        fields = ["type", "id", "host", "displayName", "page", "github", "profileImage"]

    def get_id(self, obj):
        return f"{obj.actor.local_node.url}/api/authors/{obj.actor.user.username}"

    def get_host(self, obj):
        return obj.actor.local_node.url

    def get_page(self, obj):
        return f"{obj.actor.local_node.url}/authors/{obj.actor.user.username}"


# Serializer for friendships
class FriendSerializer(serializers.ModelSerializer):
    """Serializer for friendships"""

    user1 = AuthorProfileSerializer(read_only=True)
    user2 = AuthorProfileSerializer(read_only=True)

    class Meta:
        model = Friends
        fields = ["user1", "user2"]


class FollowRequestSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="follow")
    summary = serializers.CharField()
    actor = AuthorProfileSerializer(read_only=True)
    object = AuthorProfileSerializer(read_only=True)
