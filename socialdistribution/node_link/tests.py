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
            url="http://testnode1.com",
            created_by=self.user1,
        )

        # Create author profiles
        self.author_profile1 = AuthorProfile.objects.create(
            user=self.user1,
            local_node=self.node1,
        )
        self.author_profile2 = AuthorProfile.objects.create(
            user=self.user2,
            local_node=self.node1,
        )
        self.author_profile3 = AuthorProfile.objects.create(
            user=self.user3,
            local_node=self.node1,
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

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        # Check that the context contains the correct post UUIDs
        post_ids = response.context["all_ids"]
        self.assertIn(self.post_public.uuid, post_ids)
        self.assertIn(self.post_friends_only.uuid, post_ids)
        self.assertIn(self.post_unlisted.uuid, post_ids)
        self.assertNotIn(self.post_deleted.uuid, post_ids)
        self.assertIn(self.post_user1.uuid, post_ids)

    def test_home_view_no_authentication(self):
        response = self.client.get("/")
        # Replace 'authorApp:login' with the actual URL name for your login view
        login_url = reverse("authorApp:login") + "?next=" + "/"
        self.assertRedirects(response, login_url)

    def test_home_view_friends_only_posts_visible_to_friends(self):
        # Login as user1 (friend of user2)
        self.client.login(username="user1", password="password1")

        response = self.client.get("/")

        post_ids = response.context["all_ids"]
        self.assertIn(self.post_friends_only.uuid, post_ids)

    def test_home_view_friends_only_posts_not_visible_to_non_friends(self):
        # Login as user3 (not a friend of user2)
        self.client.login(username="user3", password="password3")

        response = self.client.get("/")

        post_ids = response.context["all_ids"]
        self.assertNotIn(self.post_friends_only.uuid, post_ids)

    def test_home_view_unlisted_posts_from_following(self):
        # Login as user1 (following user3)
        self.client.login(username="user1", password="password1")

        response = self.client.get("/")

        post_ids = response.context["all_ids"]
        self.assertIn(self.post_unlisted.uuid, post_ids)

    def test_home_view_unlisted_posts_from_non_following(self):
        # Login as user2 (not following user3)
        self.client.login(username="user2", password="password2")

        response = self.client.get("/")

        post_ids = response.context["all_ids"]
        self.assertNotIn(self.post_unlisted.uuid, post_ids)

    def test_home_view_user_with_deleted_posts(self):
        # Login as user1
        self.client.login(username="user1", password="password1")

        response = self.client.get("/")

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
        author_profile4 = AuthorProfile.objects.create(
            user=user4,
            local_node=self.node1,
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

        response = self.client.get("/")

        post_ids = response.context["all_ids"]
        self.assertIn(public_post_user4.uuid, post_ids)
        self.assertIn(self.post_public.uuid, post_ids)
        self.assertNotIn(self.post_friends_only.uuid, post_ids)
        self.assertNotIn(self.post_unlisted.uuid, post_ids)
        self.assertNotIn(self.post_deleted.uuid, post_ids)

    def test_home_view_user_sees_own_posts(self):
        # Login as user1
        self.client.login(username="user1", password="password1")

        response = self.client.get("/")

        post_ids = response.context["all_ids"]
        self.assertIn(self.post_user1.uuid, post_ids)


class NodeLinkTests(APITestCase):
    def setUp(self):
        # Create a user and an author profile
        self.user = User.objects.create_user(
            username="author1",
            password="password1",
            display_name="Author One",
            is_approved=True,
        )
        self.client.login(username="author1", password="password1")
        self.author_profile = AuthorProfile.objects.create(
            user=self.user,
            local_node=Node.objects.create(
                url="http://localhost:8000", created_by=self.user
            ),
        )

        # Create an active Node for testing
        self.node = Node.objects.create(url="http://testnode.com", created_by=self.user)
        self.notification = Notification.objects.create(
            user=self.author_profile,
            message="Test notification",
            notification_type="follow_request",
        )

    def test_list_nodes(self):
        """Test listing all nodes"""
        url = reverse("node_link:node-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)  # Ensure nodes are returned

    def test_retrieve_node(self):
        """Test retrieving a specific node"""
        url = reverse("node_link:node-detail", args=[self.node.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], "http://testnode.com")

    def test_create_node(self):
        """Test creating a new node"""
        url = reverse("node_link:node-list")
        data = {"url": "http://newnode.com", "created_by": self.user.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["url"], "http://newnode.com")

    def test_update_node(self):
        """Test updating a node"""
        url = reverse("node_link:node-detail", args=[self.node.id])
        data = {"url": "http://updatednode.com", "created_by": self.user.id}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], "http://updatednode.com")

    def test_delete_node(self):
        """Test deleting a node"""
        url = reverse("node_link:node-detail", args=[self.node.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_notifications(self):
        """Test listing all notifications"""
        url = reverse("node_link:notification-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_retrieve_notification(self):
        """Test retrieving a specific notification"""
        url = reverse("node_link:notification-detail", args=[self.notification.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Test notification")

    def test_create_notification(self):
        """Test creating a new notification"""
        url = reverse("node_link:notification-list")
        data = {
            "user": self.author_profile.id,
            "message": "New notification",
            "notification_type": "new_post",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "New notification")

    def test_delete_notification(self):
        """Test deleting a notification"""
        url = reverse("node_link:notification-detail", args=[self.notification.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unread_notifications(self):
        """Test retrieving only unread notifications"""
        url = reverse("node_link:notification-unread")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        self.assertFalse(response.data[0]["is_read"])  # Ensure it's unread

    def test_home_view(self):
        """Test home view that returns filtered posts for the user"""
        url = reverse("node_link:home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("all_ids", response.context)  # Check for posts context data
