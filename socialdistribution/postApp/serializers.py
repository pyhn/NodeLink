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

    def create(self, validated_data):
        # when creating the post locally, fields that have the same name
        # in both the incoming JSON and the model will be mapped automatically, otherwise,
        # you will have to map them manually
        return Post.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.content = validated_data.get("content", instance.content)
        instance.contentType = validated_data.get("contentType", instance.contentType)
        instance.visibility = validated_data.get("visibility", instance.visibility)
        instance.save()
        return instance

    def get_id(self, obj):
        """
        constructs the full URL id for the post
        """
        host = obj.node.url.rstrip("/")
        author_id = obj.author.user.username
        post_id = obj.uuid
        return f"{host}/api/authors/{author_id}/posts/{post_id}"

    def get_author(self, obj):
        # Serialize the author using AuthorProfileSerializer
        return AuthorProfileSerializer(obj.author).data

    # check out def to_representation(self, instance) method for custom serialization


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = [
            "type",  # should be 'comment'
            "author",  # author
            "comment",  # comment
            "contentType",  # check eclass
            "published",  # ISO 8601 TIMESTAMP
            "id",  # id of the comment (check eclass) "http://nodebbbb/api/authors/111/commented/130"
            "post",  # post commented (check eclass)
            "likes",  # likes on the comment
        ]

    def create(self, validated_data):
        return Comment.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.comment = validated_data.get("comment", instance.comment)
        instance.contentType = validated_data.get("contentType", instance.contentType)
        instance.save()
        return instance


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = [
            "type",  # should be 'like'
            "author",  # author
            "published",  # ISO 8601 TIMESTAMP
            "id",  # id of the like (check eclass)
            "object",  # object liked (check eclass)
        ]

    def create(self, validated_data):
        return Like.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.object = validated_data.get("object", instance.object)
        instance.save()
        return instance
