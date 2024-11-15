from rest_framework import serializers
from postApp.models import Post, Comment, Like
from authorApp.serializers import AuthorProfileSerializer
from urllib.parse import urljoin


class PostSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    type = serializers.CharField(default="post")
    author = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "type",
            "description",
            "content",
            "visibility",
            "node",
            "author",
            "uuid",
            "contentType",
            "created_by",
        ]
        read_only_fields = ["comments", "likes", "published"]

    def get_id(self, obj):
        """
        Constructs the full URL id for the post.
        """
        host = obj.node.url.rstrip("/")
        author_id = obj.author.user.username
        post_id = obj.uuid
        return f"{host}/api/authors/{author_id}/posts/{post_id}"

    def get_author(self, obj):
        # Serialize the author using AuthorProfileSerializer
        return AuthorProfileSerializer(obj.author).data

    def create(self, validated_data):

        validated_data.pop("type")
        return Post.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.content = validated_data.get("content", instance.content)
        instance.contentType = validated_data.get("contentType", instance.contentType)
        instance.visibility = validated_data.get("visibility", instance.visibility)
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
        # Use AuthorProfileSerializer to provide full author details
        author_data = AuthorProfileSerializer(obj.author).data
        request = self.context.get("request")
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"

        # Add additional fields as required in the example JSON
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
        # Construct the full URL for the comment's ID
        request = self.context.get("request")
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"
        author_serial = obj.author.user.username
        return urljoin(base_url, f"api/authors/{author_serial}/commented/{obj.uuid}")

    def get_post(self, obj):
        # Construct the full URL for the post the comment is on
        request = self.context.get("request")
        base_url = request.build_absolute_uri("/") if request else "http://localhost/"
        post_author_serial = obj.post.author.user.username
        return urljoin(
            base_url, f"api/authors/{post_author_serial}/posts/{obj.post.uuid}"
        )

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


class LikeSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default="like")
    published = serializers.SerializerMethodField()
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        model = Like
        fields = [
            "type",
            "author",
            "published",
            "id",
            "post",
        ]

    def get_published(self, obj):
        return obj.created_at.isoformat() if hasattr(obj, "created_at") else None

    def create(self, validated_data):
        return Like.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.post = validated_data.get("post", instance.post)
        instance.save()
        return instance
