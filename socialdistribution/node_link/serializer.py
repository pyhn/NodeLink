from rest_framework import serializers
from node_link.models import (
    # Author,
    # FollowRequest,
    Post,
    Comment,
    Like,
)

# We need to refactor some of our models.py to have
# - Author
# - FollowRequest
# - Post
# - Comment
# - Like


class AuthorsSerializer(serializers.ModelSerializer):
    class Meta:
        # model = Author
        # # author fields (based on eclass)
        fields = [
            "type",  # should be 'author'
            "id",  # should be the full API URL for the author 'http://nodename/api/authors/id
            "host",  # should be the full API URL for the author's node 'http://nodename/api'
            "displayName",  # should be 'Greg Johnson' (name to be displayed)
            "github",  # should be 'http://github/gjohnson'
            "profileImage",  # check eclass
            "page",  # check eclass
        ]

    def create(self, validated_data):
        """
        creates an author object using the validated data
        """
        # return Author.objects.create(**validated_data)

    # add more methods as needed


class FollowRequestSerializer(serializers.ModelSerializer):
    class Meta:
        # model = FollowRequest
        # # follow request fields (based on eclass)
        fields = [
            "type",  # should be "follow"
            "summary",
            "actor",  # author
            "object",  # author
        ]

    def create(self, validated_data):
        """
        creates a follow request object using the validated data
        """
        # return FollowRequest.objects.create(**validated_data)

    # add more methods as needed


class PostSerializer(serializers.ModelSerializer):
    author = AuthorsSerializer(read_only=True)

    class Meta:
        model = Post
        # post fields (based on eclass)
        fields = [
            "type",  # should be 'post'
            "title",  # title of a post
            "id",  # id of the post must be the original URL on the node the post came from "http://nodebbbb/api/authors/222/posts/249"
            "description",  # check eclass
            "contentType",  # should be 'text/plain'
            "content",  # check eclass
            "author",  # author
            "comments",  # comments about the post
            "likes",
            "published",  # likes on the post  # ISO 8601 TIMESTAMP
            "visibility",  # visibility ["PUBLIC","FRIENDS","UNLISTED","DELETED"]
        ]

    def create(self, validated_data):
        """
        creates a post object using the validated data
        """
        return Post.objects.create(**validated_data)

    # add more methods as needed


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorsSerializer(read_only=True)

    class Meta:
        model = Comment
        # comment fields (based on eclass)
        fields = [
            "type",  # should be 'comment'
            "author",  # author
            "comment",  # comment
            "contentType",  # check eclass
            "published"  # ISO 8601 TIMESTAMP
            "id"  # id of the comment (check eclass) "http://nodebbbb/api/authors/111/commented/130"
            "post"  # post commented (check eclass)
            "likes",  # likes on the comment
        ]

    def create(self, validated_data):
        """
        creates a comment object using the validated data
        """
        return Comment.objects.create(**validated_data)

    # add more methods as needed


class LikeSerializer(serializers.ModelSerializer):
    author = AuthorsSerializer(read_only=True)

    class Meta:
        model = Like
        # like fields (based on eclass)
        fields = [
            "type",  # should be 'like'
            "author",  # author
            "published",  # ISO 8601 TIMESTAMP
            "id",  # id of the like (check eclass) "http://nodebbbb/api/authors/111/liked/130"
            "object",  # post/comment
        ]

    def create(self, validated_data):
        """
        creates a like object using the validated data
        """
        return Like.objects.create(**validated_data)

    # add more methods as needed
