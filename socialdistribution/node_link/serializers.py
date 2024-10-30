from rest_framework import serializers

# from node_link.models import
# Author,
# FollowRequest,


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
