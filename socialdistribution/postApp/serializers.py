from rest_framework import serializers
from postApp.models import Post, Comment, Like
from authorApp.serializers import AuthorProfileSerializer


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
    contentType = serializers.CharField(default="text/markdown")
    published = serializers.SerializerMethodField()

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
        ]

    def get_published(self, obj):
        return obj.created_at.isoformat() if hasattr(obj, "created_at") else None

    def create(self, validated_data):
        return Comment.objects.create(**validated_data)

    def update(self, instance, validated_data):
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
