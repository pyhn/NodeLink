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

    id = serializers.CharField(required=False)
    host = serializers.CharField(required=False)
    type = serializers.CharField(default="author", required=False)
    displayName = serializers.CharField(required=False)
    github = serializers.CharField(required=False, allow_blank=True)
    profileImage = serializers.CharField(required=False)
    page = serializers.CharField(required=False)

    class Meta:
        model = AuthorProfile
        fields = ["type", "id", "host", "displayName", "github", "profileImage", "page"]

    def to_representation(self, instance):
        """Custom representation for dynamically computed fields."""
        representation = {}
        representation[
            "id"
        ] = f"{instance.local_node.url}api/authors/{instance.user.username}"
        representation["host"] = instance.local_node.url
        representation["type"] = "author"

        representation["displayName"] = instance.user.display_name
        representation["github"] = instance.github

        representation["profileImage"] = str(instance.user.profileImage)
        representation["page"] = str(
            instance.local_node.url.rstrip("/")
            + reverse("authorApp:profile_display", args=[instance.user.username])
        )
        return representation

    def update(self, instance, validated_data):
        """Handle update for all fields, including related User fields."""

        # Update fields directly on AuthorProfile

        instance.user.github = validated_data.get("github", instance.github)

        # Update fields on the related User model
        instance.user.display_name = validated_data.get(
            "displayName", instance.user.display_name
        )
        instance.user.profileImage = validated_data.get(
            "profileImage", instance.user.profileImage
        )
        instance.user.save()

        # Save changes on the AuthorProfile instance itself
        instance.save()
        return instance


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
        print(f"get id obj: {obj.actor.local_node.url}")
        return f"{obj.actor.local_node.url}/api/authors/{obj.actor.user.username}"

    def get_host(self, obj):
        print(f"get host obj: {obj.actor.local_node.url}")
        return obj.actor.local_node.url

    def get_page(self, obj):
        print(f"get page obj: {obj.actor.local_node.url}")
        return f"{obj.actor.local_node.url}/authors/{obj.actor.user.username}"


# Serializer for friendships
class FriendSerializer(serializers.ModelSerializer):
    """Serializer for friendships"""

    user1 = AuthorProfileSerializer(read_only=True)
    user2 = AuthorProfileSerializer(read_only=True)

    class Meta:
        model = Friends
        fields = ["user1", "user2"]
