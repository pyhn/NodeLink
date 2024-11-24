from rest_framework import serializers
from authorApp.models import AuthorProfile, Follower, Friends, User
from django.urls import reverse
from urllib.parse import urlparse
from django.shortcuts import get_object_or_404
from node_link.models import Node
from node_link.utils.common import remove_api_suffix


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
    github = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    profileImage = serializers.CharField(required=False)
    page = serializers.CharField(required=False)

    class Meta:
        model = AuthorProfile
        fields = ["type", "id", "host", "displayName", "github", "profileImage", "page"]

    def to_representation(self, instance):
        """Custom representation for dynamically computed fields."""
        host_no_api = remove_api_suffix(instance.user.local_node.url)
        representation = {}
        representation["type"] = "author"
        representation[
            "id"
        ] = f"{instance.user.local_node.url}authors/{instance.user.user_serial}"
        representation["page"] = str(
            host_no_api
            + reverse("authorApp:profile_display", args=[instance.user.username])
        )
        representation["host"] = instance.user.local_node.url
        representation["displayName"] = instance.user.display_name
        representation["github"] = instance.github

        representation["profileImage"] = str(instance.user.profileImage)
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

    def create(self, validated_data):
        # extract data for the User model (since the author profile model has a user object)
        id_url = validated_data.get("id")
        host = validated_data.get("host")
        display_name = validated_data.get("displayName")
        github = validated_data.get("github")
        profile_image = validated_data.get("profileImage", "")
        # page = validated_data.get("page", "")

        # parse the FQID to get the serial
        fqid_parts = id_url.rstrip("/").split("/")
        serial = fqid_parts[-1]

        # retrieve the local node
        try:
            local_node = Node.objects.get(is_remote=False)
        except Node.DoesNotExist as exc:
            raise serializers.ValidationError("Local node not found.") from exc

        # determine if the user is a remote or local
        if host and host.rstrip("/") != local_node.url.rstrip("/"):
            # remote user
            parsed_host = urlparse(host)
            domain = parsed_host.netloc.replace(".", "_")
            username = f"{domain}__{serial}"

            # get the corresponding node
            node = get_object_or_404(Node, url=host, is_remote=True, is_active=True)
        else:
            # local user
            username = serial
            node = local_node

        # create or update teh user instance
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                "display_name": display_name,
                "github_user": github,
                "profileImage": profile_image,
                "local_node": node,
                "user_serial": serial,
            },
        )

        # create the author profile instance
        author_profile, _ = AuthorProfile.objects.update_or_create(
            user=user,
            defaults={
                "github": github,
                "fqid": id_url,
            },
        )

        return author_profile

    def validate(self, attrs):
        if attrs.get("type") != "author":
            raise serializers.ValidationError("Invalid type. Expected 'author'.")
        return attrs


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
        fields = ["type", "id", "page", "host", "displayName", "github", "profileImage"]

    def get_id(self, obj):
        return f"{obj.actor.user.local_node.url}authors/{obj.actor.user.user_serial}"

    def get_host(self, obj):
        return obj.actor.user.local_node.url

    def get_page(self, obj):
        host = remove_api_suffix(obj.actor.user.local_node.url)
        return f"{host}/{obj.actor.user.username}/profile"

    def create(self, validated_data):
        f_actor = get_object_or_404(
            AuthorProfile, fqid=self.initial_data["actor"]["id"]
        )
        f_object = get_object_or_404(
            AuthorProfile, fqid=self.initial_data["object"]["id"]
        )
        # Create or update follow request
        followRequest, _ = Follower.objects.update_or_create(
            actor=f_actor, object=f_object, status="p", created_by=f_actor
        )
        return followRequest


class FollowerRequestSerializer(serializers.ModelSerializer):
    """Custom Serializer for followers to match the required output format"""

    type = serializers.CharField(default="follow", read_only=True)
    summary = serializers.SerializerMethodField()
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

    def get_summary(self, obj):
        return f"{obj.actor.user.display_name} wants to follow {obj.object.user.display_name}"

    def create(self, validated_data):
        f_actor = get_object_or_404(
            AuthorProfile, fqid=self.initial_data["actor"]["id"]
        )
        f_object = get_object_or_404(
            AuthorProfile, fqid=self.initial_data["object"]["id"]
        )
        # Create or update follow request
        followRequest, _ = Follower.objects.update_or_create(
            actor=f_actor, object=f_object, status="p", created_by=f_actor
        )
        return followRequest

    def to_representation(self, instance):
        """Custom representation for dynamically computed fields."""

        f_actor_dict = AuthorProfileSerializer(instance.actor)
        f_object_dict = AuthorProfileSerializer(instance.object)

        representation = {
            "type": "follow",
            "summary": f"{instance.actor.user.display_name} wants to follow {instance.object.user.display_name}",
            "actor": f_actor_dict.to_representation(instance.actor),
            "object": f_object_dict.to_representation(instance.object),
        }
        return representation


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
            username = f"{domain}__{author_id_last_part}"

            node = get_object_or_404(Node, url=host)

            # Create or update user
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "display_name": display_name,
                    "github_user": github,
                    "profileImage": profile_image,
                    "local_node": node,
                    "user_serial": author_id_last_part,
                },
            )
            users.append(user)
        return users

    def validate(self, attrs):
        if attrs.get("type") != "authors":
            raise serializers.ValidationError("Invalid type. Expected 'authors'.")
        return attrs
