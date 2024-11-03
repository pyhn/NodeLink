# from OpenAI CHATGPT, (paraphrasing) can you test if a user can see a post based on the post's visibility?
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from authorApp.models import AuthorProfile, Friends
from postApp.models import Post
from node_link.models import Node
from rest_framework.test import APIClient
from rest_framework import status
import uuid

User = get_user_model()


class PostAPITestCase(TestCase):
    def setUp(self):
        # Create users
        self.users = {
            "author": User.objects.create_user(username="author", password="password"),
            "friend": User.objects.create_user(username="friend", password="password"),
            "non_friend": User.objects.create_user(
                username="non_friend", password="password"
            ),
        }

        # Create a Node instance
        self.node = Node.objects.create(
            url="http://localhost:8000/", created_by=self.users["author"]
        )

        # Create author profiles
        self.profiles = {
            "author": AuthorProfile.objects.create(
                user=self.users["author"], local_node=self.node
            ),
            "friend": AuthorProfile.objects.create(
                user=self.users["friend"], local_node=self.node
            ),
            "non_friend": AuthorProfile.objects.create(
                user=self.users["non_friend"], local_node=self.node
            ),
        }

        # Establish friendship between author and friend
        Friends.objects.create(
            user1=self.profiles["author"],
            user2=self.profiles["friend"],
            status=True,
            created_by=self.profiles["author"],
        )

        # Create posts with different visibilities
        self.posts = {
            "public_post": Post.objects.create(
                title="Public Post",
                description="A public post.",
                content="This is a public post.",
                visibility="p",
                node=self.node,
                author=self.profiles["author"],
                uuid=uuid.uuid4(),
                contentType="text/plain",
                created_by=self.profiles["author"],
            ),
            "friends_post": Post.objects.create(
                title="Friends Post",
                description="A friends-only post.",
                content="This is a friends-only post.",
                visibility="fo",
                node=self.node,
                author=self.profiles["author"],
                uuid=uuid.uuid4(),
                contentType="text/plain",
                created_by=self.profiles["author"],
            ),
            "unlisted_post": Post.objects.create(
                title="Unlisted Post",
                description="An unlisted post.",
                content="This is an unlisted post.",
                visibility="u",
                node=self.node,
                author=self.profiles["author"],
                uuid=uuid.uuid4(),
                contentType="text/plain",
                created_by=self.profiles["author"],
            ),
        }

        # Initialize API client
        self.client = APIClient()

    def test_get_public_post_unauthenticated(self):
        """Unauthenticated user can retrieve public post"""
        url = reverse(
            "postApp:post_detail_api",
            kwargs={
                "author_serial": self.author_user.username,
                "post_serial": self.public_post.uuid,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_friends_post_unauthenticated(self):
        """Unauthenticated user cannot retrieve friends-only post"""
        url = reverse(
            "postApp:post_detail_api",
            kwargs={
                "author_serial": self.author_user.username,
                "post_serial": self.friends_post.uuid,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_public_post_authenticated_non_friend(self):
        """Authenticated non-friend can retrieve public post"""
        self.client.login(username="non_friend", password="password")
        url = reverse(
            "postApp:post_detail_api",
            kwargs={
                "author_serial": self.author_user.username,
                "post_serial": self.public_post.uuid,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.logout()
