from rest_framework import serializers
from postApp.models import Post, Comment, Like
from authorApp.models import AuthorProfile, User
from node_link.models import Node
from authorApp.serializers import AuthorProfileSerializer
from urllib.parse import urljoin, urlparse
from django.shortcuts import get_object_or_404
import uuid
from datetime import datetime


class PostSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    type = serializers.CharField(default="post", read_only=True)
    author = serializers.SerializerMethodField(read_only=True)
    comments = serializers.SerializerMethodField(read_only=True)
    likes = serializers.SerializerMethodField(read_only=True)
    page = serializers.SerializerMethodField()
    published = serializers.DateTimeField(
        source="created_at", format="iso-8601", read_only=True
    )

    class Meta:
        model = Post
        fields = [
            "type",
            "title",
            "id",
            "page",
            "description",
            "contentType",
            "content",
            "author",
            "comments",
            "likes",
            "published",
            "visibility",
        ]

    def get_id(self, obj):
        host = obj.node.url.rstrip("/")
        author_id = obj.author.user.username
        post_id = obj.uuid
        return f"{host}/api/authors/{author_id}/posts/{post_id}"

    def get_author(self, obj):
        return {
            "type": "author",
            "id": f"{obj.author.user.local_node.url.rstrip('/')}/api/authors/{obj.author.user.username}",
            "host": obj.author.user.local_node.url.rstrip("/") + "/",
            "displayName": obj.author.user.display_name,
            "github": obj.author.github,
            "profileImage": obj.author.user.profileImage.url,
            "page": f"{obj.author.user.local_node.url.rstrip('/')}/authors/{obj.author.user.username}",
        }

    def get_comments(self, obj):
        comments = obj.comments.all().order_by("-created_at")[:5]
        return {
            "type": "comments",
            "page": f"{obj.node.url.rstrip('/')}/authors/{obj.author.user.username}/posts/{obj.uuid}",
            "id": f"{obj.node.url.rstrip('/')}/api/authors/{obj.author.user.username}/posts/{obj.uuid}/comments",
            "page_number": 1,
            "size": 5,
            "count": obj.comments.count(),
            "src": CommentSerializer(comments, many=True, context=self.context).data,
        }

    def get_likes(self, obj):
        likes = obj.postliked.all().order_by("-created_at")[:5]
        return {
            "type": "likes",
            "page": f"{obj.node.url.rstrip('/')}/authors/{obj.author.user.username}/posts/{obj.uuid}",
            "id": f"{obj.node.url.rstrip('/')}/api/authors/{obj.author.user.username}/posts/{obj.uuid}/likes",
            "page_number": 1,
            "size": 5,
            "count": obj.postliked.count(),
            "src": LikeSerializer(likes, many=True, context=self.context).data,
        }

    def get_page(self, obj):
        """
        Constructs the HTML URL for the post.
        """
        host = obj.node.url.rstrip("/")
        author_id = obj.author.user.username
        post_id = obj.uuid
        return f"{host}/authors/{author_id}/posts/{post_id}"

    def validate_author(self, value):
        """
        Validate or create the author field from the incoming data.
        """
        if not value or not isinstance(value, dict):
            raise serializers.ValidationError("Author data is missing or malformed.")

        author_id = value.get("id")
        host = value.get("host")
        display_name = value.get("displayName", "Unknown Author")
        github = value.get("github", "")
        profile_image = value.get("profileImage", "")

        # Extract username from the author ID
        try:
            username = author_id.rstrip("/").split("/")[-1]
            domain = urlparse(host).netloc
            username = (
                f"{domain}__{username}"  # Ensure unique username for remote authors
            )
        except Exception as e:
            raise serializers.ValidationError(f"Invalid author ID or host: {e}")

        # Check if the user exists, otherwise create it
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "display_name": display_name,
                "github_user": github,
                "profileImage": profile_image,
            },
        )

        # Ensure the user is associated with the correct node
        if not user.local_node:
            node = Node.objects.get_object_or_404(Node, url=host)
            user.local_node = node
            user.save()

        # Check if the author profile exists, otherwise create it
        author, _ = AuthorProfile.objects.get_or_create(user=user)

        return author

    def to_internal_value(self, data):
        """
        Convert incoming JSON into a validated internal Python representation.
        """
        validated_data = super().to_internal_value(data)
        author_data = data.get("author")
        validated_data["author"] = self.validate_author(author_data)
        return validated_data

    def create(self, validated_data):
        """
        Create a Post instance with required fields.
        """
        # Extract author from validated data
        author = validated_data.pop("author", None)
        if not author:
            raise serializers.ValidationError("Author is required to create a post.")

        # Set the created_by field
        validated_data["created_by"] = author

        # Create the Post instance
        return Post.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update a Post instance while handling fields from MixinApp.
        """
        # Update modifiable fields
        for field in ["title", "description", "content", "contentType", "visibility"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Update updated_by field
        user = self.context["request"].user.author_profile
        instance.updated_by = user
        instance.updated_at = datetime.now()

        # Save the updated instance
        instance.save()
        return instance


class CommentSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="comment")
    author = serializers.SerializerMethodField()
    contentType = serializers.SerializerMethodField()  # Custom field for content type
    published = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    post = serializers.SerializerMethodField()
    page = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "type",
            "author",
            "content",
            "contentType",
            "published",
            "id",
            "post",
            "page",
        ]

    def get_author(self, obj):
        if isinstance(obj, dict):
            # If obj is a dict, assume it's already serialized
            return obj.get("author", {})
        else:
            # If obj is a model instance, serialize the author properly
            author_data = AuthorProfileSerializer(obj.author).data
            request = self.context.get("request")
            base_url = (
                request.build_absolute_uri("/") if request else "http://localhost/"
            )

            author_data.update(
                {
                    "type": "author",
                    "page": urljoin(base_url, f"authors/{obj.author.user.username}"),
                    "host": base_url,
                }
            )
            return author_data

    def get_contentType(self, obj):
        # Return a default content type
        return "text/markdown"  # or any other default value you prefer

    def get_published(self, obj):
        # Provide ISO 8601 format for published field
        return obj.created_at.isoformat() if hasattr(obj, "created_at") else None

    def get_id(self, obj):
        if isinstance(obj, dict):
            # Handle dict scenario
            return obj.get("id", "")
        else:
            # Handle model instance scenario
            request = self.context.get("request")
            base_url = (
                request.build_absolute_uri("/") if request else "http://localhost/"
            )
            author_serial = obj.author.user.username
            return urljoin(
                base_url, f"api/authors/{author_serial}/commented/{obj.uuid}"
            )

    def get_post(self, obj):
        # Construct the full URL for the post the comment is on
        request = self.context.get("request")
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"
        post_author_serial = obj.post.author.user.username
        return urljoin(
            base_url, f"api/authors/{post_author_serial}/posts/{obj.post.uuid}"
        )

    def to_internal_value(self, data):
        """
        Custom logic to parse incoming data and ensure only required fields are processed.
        """
        validated_data = {}

        # Extract and validate content
        if "content" in data:
            validated_data["content"] = data["content"]
        else:
            raise serializers.ValidationError({"content": "Content is required."})

        # Parse and validate post URL
        post_url = data.get("post", "")
        if post_url:
            try:
                post_uuid = post_url.rstrip("/").split("/")[-1]
                validated_data["post"] = Post.objects.get(uuid=post_uuid)
            except Post.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"post": "Invalid post URL or UUID."}
                ) from exc
        else:
            raise serializers.ValidationError({"post": "Post is required."})

        # Parse and validate author URL
        author_id = data.get("author", {}).get("id", "")
        if author_id:
            try:
                author_username = author_id.rstrip("/").split("/")[-1]
                validated_data["author"] = AuthorProfile.objects.get(
                    user__username=author_username
                )
            except AuthorProfile.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"author": "Invalid author ID."}
                ) from exc
        else:
            raise serializers.ValidationError({"author": "Author is required."})

        # Automatically set visibility to default ("p")
        validated_data["visibility"] = "p"

        # Automatically generate a new UUID
        validated_data["uuid"] = uuid.uuid4()

        # Automatically set created_by to the authenticated user (if available)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                validated_data["created_by"] = AuthorProfile.objects.get(
                    user=request.user
                )
            except AuthorProfile.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {
                        "created_by": "Authenticated user is not linked to an author profile."
                    }
                ) from exc

        return validated_data

    def get_page(self, obj):
        # Return the URL to view the comment or the post in HTML format
        request = self.context.get("request")
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"
        post_author_serial = obj.post.author.user.username
        return urljoin(base_url, f"authors/{post_author_serial}/posts/{obj.post.uuid}")

    def create(self, validated_data):
        # Override create to use the validated data without model changes
        return Comment.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Override update to allow updating without model changes
        instance.content = validated_data.get("content", instance.content)
        instance.save()
        return instance


class CommentsSerializer(serializers.Serializer):
    type = serializers.CharField(default="comments")
    page = serializers.CharField()  # URL of the comments page
    id = serializers.CharField()  # ID of the comments API
    page_number = serializers.IntegerField()
    size = serializers.IntegerField()
    count = serializers.IntegerField()
    src = serializers.SerializerMethodField()

    def get_src(self, obj):
        # Serialize the queryset of comments
        comments = obj.get("src", [])
        return CommentSerializer(comments, many=True, context=self.context).data


class LikeSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="like")
    published = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = [
            "type",
            "author",
            "published",
            "id",
            "object",
        ]

    def get_published(self, obj):
        return obj.created_at.isoformat() if hasattr(obj, "created_at") else None

    def get_object(self, obj):
        return f"{obj.post.author.user.local_node.url}/authors/{obj.post.author.user.username}/posts/{obj.post.uuid}"

    def get_author(self, obj):
        return AuthorProfileSerializer(obj.author).data
