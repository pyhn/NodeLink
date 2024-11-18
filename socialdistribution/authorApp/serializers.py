from rest_framework import serializers
from authorApp.models import AuthorProfile, Follower, Friends, User
from django.urls import reverse
from urllib.parse import urlparse
from django.shortcuts import get_object_or_404
from node_link.models import Node

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
        ] = f"{instance.user.local_node.url}api/authors/{instance.user.username}"
        representation["host"] = instance.user.local_node.url
        representation["type"] = "author"

        representation["displayName"] = instance.user.display_name
        representation["github"] = instance.github

        representation["profileImage"] = str(instance.user.profileImage)
        representation["page"] = str(
            instance.user.local_node.url.rstrip("/")
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

    type = serializers.CharField(default="follow", read_only=True)
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
        return f"{obj.actor.user.local_node.url}/api/authors/{obj.actor.user.username}"

    def get_host(self, obj):
        return obj.actor.user.local_node.url

    def get_page(self, obj):
        return f"{obj.actor.user.local_node.url}/authors/{obj.actor.user.username}"


# Serializer for friendships
class FriendSerializer(serializers.ModelSerializer):
    """Serializer for friendships"""

    user1 = AuthorProfileSerializer(read_only=True)
    user2 = AuthorProfileSerializer(read_only=True)

    class Meta:
        model = Friends
        fields = ["user1", "user2"]


class AuthorToUserSerializer(serializers.Serializer):
    type = serializers.CharField()
    authors = serializers.ListField()

    def create(self, validated_data):
        users = []
        for author_data in validated_data["authors"]:
            # Extract fields
            id_url = author_data.get("id")
            host = author_data.get("host")
            display_name = author_data.get("displayName")
            github = author_data.get("github")
            profile_image = author_data.get("profileImage")

            # Generate unique username (domain + last part of the ID)
            domain = urlparse(host).netloc
            author_id_last_part = id_url.rstrip("/").split("/")[-1]
            username = f"{domain}_{author_id_last_part}"
            node = get_object_or_404(Node, url=host)
            # Create or update user
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "display_name": display_name,
                    "github_user": github,
                    "profileImage": profile_image,
                    "local_node": node,
                },
            )
            users.append(user)
        return users

    def validate(self, data):
        if data.get("type") != "authors":
            raise serializers.ValidationError("Invalid type. Expected 'authors'.")
        return data
