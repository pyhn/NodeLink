from rest_framework import serializers
from postApp.models import Post, Comment, Like
from authorApp.models import AuthorProfile, User
from node_link.models import Node
from authorApp.serializers import AuthorProfileSerializer
from urllib.parse import urljoin, urlparse
from django.shortcuts import get_object_or_404
import uuid
from datetime import datetime
from node_link.utils.common import remove_api_suffix


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
    visibility = serializers.CharField()  # Make this writable
    contentType = serializers.CharField()  # Make this writable

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
        return obj.fqid

    def get_visibility(self, obj):
        return obj.get_visibility_display()

    def get_contentType(self, obj):
        return obj.get_contentType_display()

    def get_author(self, obj):
        host = obj.node.url
        host_no_api = remove_api_suffix(host)
        return {
            "type": "author",
            "id": f"{obj.author.user.local_node.url.rstrip('/')}/authors/{obj.author.user.user_serial}",
            "host": obj.author.user.local_node.url.rstrip("/") + "/",
            "displayName": obj.author.user.display_name,
            "github": obj.author.github,
            "page": f"{host_no_api}/{obj.author.user.username}/profile",
            "profileImage": obj.author.user.profileImage.url,
        }

    def get_comments(self, obj):
        comments = obj.comments.all().order_by("-created_at")[:5]
        host = obj.node.url
        host_no_api = remove_api_suffix(host)
        return {
            "type": "comments",
            "page": f"{host_no_api}/{obj.author.user.username}/posts_list/{obj.uuid}",
            "id": f"{obj.node.url.rstrip('/')}/authors/{obj.author.user.user_serial}/posts/{obj.post_serial}/comments",
            "page_number": 1,
            "size": 5,
            "count": obj.comments.count(),
            "src": CommentSerializer(comments, many=True, context=self.context).data,
        }

    def get_likes(self, obj):
        likes = obj.postliked.all().order_by("-created_at")[:5]
        host = obj.node.url
        host_no_api = remove_api_suffix(host)
        return {
            "type": "likes",
            "page": f"{host_no_api}/{obj.author.user.username}/posts_list/{obj.uuid}",
            "id": f"{host}authors/{obj.author.user.user_serial}/posts/{obj.post_serial}/likes",
            "page_number": 1,
            "size": 5,
            "count": obj.postliked.count(),
            "src": LikeSerializer(likes, many=True, context=self.context).data,
        }

    def get_page(self, obj):
        """
        Constructs the HTML URL for the post.
        """
        host = remove_api_suffix(obj.node.url)
        author_id = obj.author.user.username
        post_id = obj.uuid
        return f"{host}/{author_id}/posts_list/{post_id}"

    def validate_author(self, value):
        """
        Validate or create the author field from the incoming data.
        """
        if not value or not isinstance(value, dict):
            raise serializers.ValidationError("Author data is missing or malformed.")

        author_id = value.get("id")
        host = value.get("host")

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
        author = get_object_or_404(AuthorProfile, fqid=author_id)

        return author

    def to_representation(self, instance):
        """
        Custom representation to map internal values to external human-readable values.
        """
        representation = super().to_representation(instance)

        # Map visibility and contentType to their human-readable forms
        visibility_mapping = {
            "p": "PUBLIC",
            "u": "UNLISTED",
            "fo": "FRIENDS",
            "d": "DELETED",
        }
        content_type_mapping = {
            "p": "text/plain",
            "m": "text/markdown",
            "png": "image/png;base64",
            "jpeg": "image/jpeg;base64",
            "a": "application/base64",
        }

        representation["visibility"] = visibility_mapping.get(
            instance.visibility, instance.visibility
        )
        representation["contentType"] = content_type_mapping.get(
            instance.contentType, instance.contentType
        )

        return representation

    def to_internal_value(self, data):
        """
        Convert incoming JSON into a validated internal Python representation.
        """
        print("Incoming ID:", data.get("id"))
        if "id" in data:
            # Extract the `post_serial` from the incoming `id`
            post_serial = data["id"].rstrip("/").split("/")[-1]
            data[
                "post_serial"
            ] = post_serial  # Add post_serial to data for further processing

        # Map visibility and contentType to internal values
        if data.get("visibility"):
            data["visibility"] = self.map_visibility(data["visibility"])
        if data.get("contentType"):
            data["contentType"] = self.map_content_type(data["contentType"])

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

        contentType = validated_data.get("contentType")
        visibility = validated_data.get("visibility")

        if not contentType or not visibility:
            raise serializers.ValidationError(
                "ContentType or visibility is missing or invalid."
            )

        # Set the created_by field
        validated_data["created_by"] = author
        validated_data["author"] = author
        validated_data["updated_by"] = author

        # Fetch and set the Node object based on the host in the author data
        author_data = self.initial_data.get("author", {})
        host = author_data.get("host")
        try:
            node = Node.objects.get(url=host)
            validated_data["node"] = node
        except Node.DoesNotExist as exc:
            raise serializers.ValidationError(
                f"No Node found for host: {host}"
            ) from exc

        # Extract or construct the post_serial
        incoming_id = self.initial_data.get(
            "id", None
        )  # Use `initial_data` to capture the incoming data
        if incoming_id:
            # Extract `post_serial` from the incoming `id`
            post_serial = incoming_id.rstrip("/").split("/")[-1]
            validated_data["post_serial"] = post_serial
            validated_data["fqid"] = incoming_id

        # Construct the `fqid` using `node`, `author`, and `post_serial`
        if "post_serial" in validated_data:
            validated_data[
                "fqid"
            ] = f"{node.url.rstrip('/')}authors/{author.user.user_serial}/posts/{validated_data['post_serial']}"

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

    def map_visibility(self, visibility):
        """
        Map external visibility to internal representation.
        """
        visibility_mapping = {
            "PUBLIC": "p",
            "UNLISTED": "u",
            "FRIENDS": "fo",
            "DELETED": "d",
        }
        return visibility_mapping.get(visibility.upper(), visibility)

    def map_content_type(self, content_type):
        """
        Map external contentType to internal representation.
        """
        content_type_mapping = {
            "text/plain": "p",
            "text/markdown": "m",
            "image/png;base64": "png",
            "image/jpeg;base64": "jpeg",
            "application/base64": "a",
        }
        return content_type_mapping.get(content_type.lower(), content_type)


class CommentSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="comment")
    author = serializers.SerializerMethodField()
    contentType = serializers.SerializerMethodField()  # Custom field for content type
    published = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    post = serializers.SerializerMethodField()
    page = serializers.SerializerMethodField()
    comment = serializers.CharField(source="content")
    likes = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "type",
            "author",
            "comment",
            "contentType",
            "published",
            "id",
            "post",
            "page",
            "likes",
        ]

    def get_author(self, obj):
        if isinstance(obj, dict):
            # If obj is a dict, assume it's already serialized
            return obj.get("author", {})
        else:
            # If obj is a model instance, serialize the author properly
            author_data = AuthorProfileSerializer(obj.author).data
            host = obj.author.user.local_node.url
            host_no_api = remove_api_suffix(host)
            author_data.update(
                {
                    "type": "author",
                    "page": f"{host_no_api}/{obj.author.user.username}/profile",
                    "host": host,
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
            print(f"object {obj}")
            return obj.get("id", "")
        else:
            # Handle model instance scenario
            return obj.fqid

    def get_post(self, obj):
        # Construct the full URL for the post the comment is on
        host = obj.author.user.local_node.url
        return f"{host}authors/{obj.post.author.user.user_serial}/posts/{obj.post.post_serial}"

    def get_page(self, obj):
        host = obj.author.user.local_node.url
        host_no_api = remove_api_suffix(host)
        return (
            f"{host_no_api}/{obj.post.author.user.username}/posts_list/{obj.post.uuid}"
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

    def get_likes(self, obj):
        """
        Construct the likes field for the comment.
        Since likes are not implemented, src is empty and count is zero.
        """
        comment_id = obj.fqid
        host_no_api = remove_api_suffix(obj.post.node.url)
        post_author = obj.post.author
        post = obj.post
        return {
            "type": "likes",
            "id": f"{comment_id}/likes",
            "page": f"{host_no_api}/{post_author.user.username}/posts_list/{post.uuid}",
            "page_number": 1,
            "size": 5,
            "count": 0,
            "src": [],  # No likes implemented, so this is empty
        }

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
    id = serializers.SerializerMethodField()

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
        return f"{obj.post.author.user.local_node.url}authors/{obj.post.author.user.username}/posts/{obj.post.uuid}"

    def get_author(self, obj):
        return AuthorProfileSerializer(obj.author).data

    def get_id(self, obj):
        return obj.fqid
