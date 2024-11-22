# node_link/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status  # You can keep this if you're using DRF status codes

from authorApp.models import AuthorProfile, Friends, Follower
from postApp.models import Post
from node_link.models import Node, Notification

User = get_user_model()


class HomeViewTestCase(TestCase):
    def setUp(self):
        # Get the custom User model
        # Initialize the test client
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            username="user1",
            password="password1",
            display_name="User One",
            email="user1@example.com",
            is_approved=True,
        )

        self.user2 = User.objects.create_user(
            username="user2",
            password="password2",
            display_name="User Two",
            email="user2@example.com",
            is_approved=True,
        )

        self.user3 = User.objects.create_user(
            username="user3",
            password="password3",
            display_name="User Three",
            email="user3@example.com",
            is_approved=True,
        )

        # Create nodes
        self.node1 = Node.objects.create(
            url="http://testnode1.com/api/",
            created_by=self.user1,
        )

        self.user1.local_node = self.node1
        self.user1.user_serial = self.user1.username
        self.user1.save()

        self.user2.local_node = self.node1
        self.user2.user_serial = self.user2.username
        self.user2.save()

        self.user3.local_node = self.node1
        self.user3.user_serial = self.user3.username
        self.user3.save()

        # Create author profiles
        self.author_profile1 = AuthorProfile.objects.create(
            user=self.user1,
        )
        self.author_profile2 = AuthorProfile.objects.create(
            user=self.user2,
        )
        self.author_profile3 = AuthorProfile.objects.create(
            user=self.user3,
        )

        # Create friendship between user1 and user2
        Friends.objects.create(
            user1=min(self.author_profile1, self.author_profile2, key=lambda x: x.id),
            user2=max(self.author_profile1, self.author_profile2, key=lambda x: x.id),
            created_by=self.author_profile1,
        )

        # user1 follows user3
        Follower.objects.create(
            actor=self.author_profile1,
            object=self.author_profile3,
            status="a",  # Accepted
            created_by=self.author_profile1,
        )

        # Create posts with different visibility settings
        self.post_public = Post.objects.create(
            author=self.author_profile2,
            content="Public post by user2",
            visibility="p",  # Public
            title="Public Post",
            description="Description of public post",
            contentType="text/plain",  # Changed to 'contentType'
            created_by=self.author_profile2,
            node=self.node1,
        )

        self.post_friends_only = Post.objects.create(
            author=self.author_profile2,
            content="Friends-only post by user2",
            visibility="fo",  # Friends-only
            title="Friends-only Post",
            description="Description of friends-only post",
            contentType="text/plain",
            created_by=self.author_profile2,
            node=self.node1,
        )

        self.post_unlisted = Post.objects.create(
            author=self.author_profile3,
            content="Unlisted post by user3",
            visibility="u",  # Unlisted
            title="Unlisted Post",
            description="Description of unlisted post",
            contentType="text/plain",
            created_by=self.author_profile3,
            node=self.node1,
        )

        self.post_deleted = Post.objects.create(
            author=self.author_profile2,
            content="Deleted post by user2",
            visibility="d",  # Deleted
            title="Deleted Post",
            description="Description of deleted post",
            contentType="text/plain",
            created_by=self.author_profile2,
            node=self.node1,
        )

        # Create a post by user1
        self.post_user1 = Post.objects.create(
            author=self.author_profile1,
            content="Post by user1",
            visibility="p",
            title="User1 Post",
            description="Description of user1 post",
            contentType="text/plain",
            created_by=self.author_profile1,
            node=self.node1,
        )

    def test_home_view_authenticated_user(self):
        # Login as user1
        self.client.login(username="user1", password="password1")

        url = reverse("node_link:home", kwargs={"username": "user1"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that the context contains the correct post UUIDs
        post_ids = response.context["all_ids"]
        self.assertIn(self.post_public.uuid, post_ids)
        self.assertIn(self.post_friends_only.uuid, post_ids)
        self.assertIn(self.post_unlisted.uuid, post_ids)
        self.assertNotIn(self.post_deleted.uuid, post_ids)
        self.assertIn(self.post_user1.uuid, post_ids)

    def test_home_view_no_authentication(self):
        url = reverse("node_link:home", kwargs={"username": "test"})
        response = self.client.get(url)
        print(f"pyhn {response}")
        # Replace 'authorApp:login' with the actual URL name for your login view
        login_url = reverse("authorApp:login") + "?next=" + "/test/"
        self.assertRedirects(response, login_url)

    def test_home_view_friends_only_posts_visible_to_friends(self):
        # Login as user1 (friend of user2)
        self.client.login(username="user1", password="password1")

        url = reverse("node_link:home", kwargs={"username": "user1"})
        response = self.client.get(url)

        post_ids = response.context["all_ids"]
        self.assertIn(self.post_friends_only.uuid, post_ids)

    def test_home_view_friends_only_posts_not_visible_to_non_friends(self):
        # Login as user3 (not a friend of user2)
        self.client.login(username="user3", password="password3")

        url = reverse("node_link:home", kwargs={"username": "user1"})
        response = self.client.get(url)
        print(f"pyhn {response}")
        post_ids = response.context["all_ids"]
        self.assertNotIn(self.post_friends_only.uuid, post_ids)

    def test_home_view_unlisted_posts_from_following(self):
        # Login as user1 (following user3)
        self.client.login(username="user1", password="password1")

        url = reverse("node_link:home", kwargs={"username": "user1"})
        response = self.client.get(url)

        post_ids = response.context["all_ids"]
        self.assertIn(self.post_unlisted.uuid, post_ids)

    def test_home_view_unlisted_posts_from_non_following(self):
        # Login as user2 (not following user3)
        self.client.login(username="user2", password="password2")

        url = reverse("node_link:home", kwargs={"username": "user2"})
        response = self.client.get(url)

        post_ids = response.context["all_ids"]
        self.assertNotIn(self.post_unlisted.uuid, post_ids)

    def test_home_view_user_with_deleted_posts(self):
        # Login as user1
        self.client.login(username="user1", password="password1")

        url = reverse("node_link:home", kwargs={"username": "user1"})
        response = self.client.get(url)

        post_ids = response.context["all_ids"]
        self.assertNotIn(self.post_deleted.uuid, post_ids)

    def test_home_view_user_with_no_friends_followers(self):
        # Login as a new user with no friends or followers
        user4 = User.objects.create_user(
            username="user4",
            password="password4",
            display_name="User Four",
            email="user4@example.com",
            is_approved=True,
        )

        user4.local_node = self.node1
        user4.save()

        author_profile4 = AuthorProfile.objects.create(
            user=user4,
        )

        # Create a public post by user4
        public_post_user4 = Post.objects.create(
            author=author_profile4,
            content="Public post by user4",
            visibility="p",  # Public
            title="User4 Public Post",
            description="Description of user4 public post",
            contentType="text/plain",
            created_by=author_profile4,
            node=self.node1,
        )

        self.client.login(username="user4", password="password4")

        url = reverse("node_link:home", kwargs={"username": "user4"})
        response = self.client.get(url)

        post_ids = response.context["all_ids"]
        self.assertIn(public_post_user4.uuid, post_ids)
        self.assertIn(self.post_public.uuid, post_ids)
        self.assertNotIn(self.post_friends_only.uuid, post_ids)
        self.assertNotIn(self.post_unlisted.uuid, post_ids)
        self.assertNotIn(self.post_deleted.uuid, post_ids)

    def test_home_view_user_sees_own_posts(self):
        # Login as user1
        self.client.login(username="user1", password="password1")

        url = reverse("node_link:home", kwargs={"username": "user1"})
        response = self.client.get(url)

        post_ids = response.context["all_ids"]
        self.assertIn(self.post_user1.uuid, post_ids)
