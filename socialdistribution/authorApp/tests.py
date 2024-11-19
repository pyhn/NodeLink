from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import auth
from django.contrib.messages import get_messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from .models import AuthorProfile, User, Friends, Follower
from node_link.models import Node
from postApp.models import Post


# Set up the User model
User = get_user_model()


class AuthorAppViewsTestCase(TestCase):
    def setUp(self):
        # Create test users with display_name set
        self.user1 = User.objects.create_user(
            username="testuser1",
            password="testpassword1",
            is_approved=True,
            email="testuser1@example.com",
            first_name="Test",
            last_name="User1",
            display_name="Test User1",  # Set display_name here
        )

        self.user2 = User.objects.create_user(
            username="testuser2",
            password="testpassword2",
            is_approved=True,
            email="testuser2@example.com",
            first_name="Test",
            last_name="User2",
            display_name="Test User2",  # Set display_name here
        )

        # Create a Node with timezone-aware datetime fields
        self.node = Node.objects.create(
            url="http://testnode.com",
            created_by=self.user1,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            # Ensure 'deleted_at' is timezone-aware if you set it
            # deleted_at=timezone.now(),  # Uncomment if needed
        )

        self.user2.local_node = self.node
        self.user2.save()

        self.user1.local_node = self.node
        self.user1.save()

        # Create AuthorProfiles without invalid fields
        self.author_profile1 = AuthorProfile.objects.create(
            user=self.user1,
            # Add other fields as necessary
            github="",
            github_token="",
            github_user="",
        )

        self.author_profile2 = AuthorProfile.objects.create(
            user=self.user2,
            # Add other fields as necessary
            github="",
            github_token="",
            github_user="",
        )

        # Initialize the test client
        self.client = Client()

    # Tests for signup_view
    def test_signup_view_get(self):
        """
        Test that the signup_view returns a 200 status code for GET requests.
        """
        response = self.client.get(reverse("authorApp:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")

    def test_signup_view_post_valid_data(self):
        """
        Test that the signup_view creates a new user with valid POST data.
        """
        form_data = {
            "username": "newuser",
            "password1": "newpassword123",
            "password2": "newpassword123",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "description": "I am a new user.",
            "display_name": "New User",  # Include display_name as it's required
        }
        self.client.post(reverse("authorApp:signup"), data=form_data)
        # Check that the user was created
        self.assertTrue(User.objects.filter(username="newuser").exists())
        new_user = User.objects.get(username="newuser")
        self.assertEqual(new_user.email, "newuser@example.com")
        self.assertEqual(new_user.first_name, "New")
        self.assertEqual(new_user.last_name, "User")
        self.assertEqual(new_user.display_name, "New User")
        self.assertEqual(new_user.description, "I am a new user.")
        # Check that the AuthorProfile was created
        self.assertTrue(AuthorProfile.objects.filter(user=new_user).exists())
        # Check that the user is not approved yet (if applicable)
        self.assertFalse(new_user.is_approved)
        # Check that the user is logged in (if your app logs in users upon signup)
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, "newuser")

    def test_signup_view_post_invalid_data(self):
        """
        Test that the signup_view handles invalid POST data.
        """
        form_data = {
            "username": "newuser",
            "password1": "newpassword123",
            "password2": "wrongpassword",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "description": "I am a new user.",
        }
        response = self.client.post(reverse("authorApp:signup"), data=form_data)
        # Should render the signup page again with errors
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")
        self.assertContains(response, "Please correct the errors below.")
        # User should not be created
        self.assertFalse(User.objects.filter(username="newuser").exists())

    # Tests for login_view
    def test_login_view_get(self):
        """
        Test that the login_view returns a 200 status code for GET requests.
        """
        response = self.client.get(reverse("authorApp:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    def test_login_view_post_valid_credentials(self):
        """
        Test that the login_view logs in the user with valid credentials.
        """
        response = self.client.post(
            reverse("authorApp:login"),
            data={
                "username": "testuser1",
                "password": "testpassword1",
            },
        )
        # Generate the URL with the required 'username' argument
        home_url = reverse("node_link:home", kwargs={"username": "testuser1"})

        # Assert that the response redirects to the correct home URL
        self.assertRedirects(response, home_url)

        # Check that the user is logged in
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, "testuser1")

    def test_login_view_post_invalid_credentials(self):
        """
        Test that the login_view handles invalid credentials.
        """
        response = self.client.post(
            reverse("authorApp:login"),
            data={
                "username": "testuser1",
                "password": "wrongpassword",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")
        self.assertContains(response, "Invalid username or password.")
        # Check that the user is not logged in
        user = auth.get_user(self.client)
        self.assertFalse(user.is_authenticated)

    # Tests for logout_view
    def test_logout_view(self):
        """
        Test that the logout_view logs out the user.
        """
        # First, log in the user
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("authorApp:logout"))
        self.assertRedirects(response, reverse("authorApp:login"))
        # Check that the user is logged out
        user = auth.get_user(self.client)
        self.assertFalse(user.is_authenticated)

    # Tests for profile_display
    def test_profile_display_view_own_profile(self):
        """
        Test that an approved user can view their own profile.
        """
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(
            reverse("authorApp:profile_display", args=["testuser1"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user_profile.html")
        self.assertContains(response, "Test User1")

    def test_profile_display_view_other_profile(self):
        """
        Test that an approved user can view another user's profile.
        """
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(
            reverse("authorApp:profile_display", args=["testuser2"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user_profile.html")
        self.assertContains(response, "Test User2")

    def test_profile_display_unapproved_user(self):
        """
        Test that an unapproved user is redirected when trying to view a profile.
        """
        # Create an unapproved user
        unapproved_user = User.objects.create_user(
            username="unapproved_user",
            password="unapprovedpassword",
            is_approved=False,
            local_node=self.node,
        )
        AuthorProfile.objects.create(
            user=unapproved_user,
        )
        self.client.login(username="unapproved_user", password="unapprovedpassword")
        response = self.client.get(
            reverse("authorApp:profile_display", args=["testuser1"])
        )
        # Should redirect to login with a warning message
        self.assertRedirects(response, reverse("authorApp:login"))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Your account is not approved" in str(message) for message in messages)
        )

    # Tests for friends_page
    def test_friends_page_view(self):
        """
        Test that an approved user can view the friends page.
        """
        # Establish friendship
        user1, user2 = sorted(
            [self.author_profile1, self.author_profile2], key=lambda x: x.id
        )
        Friends.objects.create(
            user1=user1,
            user2=user2,
            created_by=self.author_profile1,
        )
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("authorApp:friends_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser2")

    def test_friends_page_unapproved_user(self):
        """
        Test that an unapproved user cannot view the friends page.
        """
        # Create an unapproved user
        unapproved_user = User.objects.create_user(
            username="unapproved_user",
            password="unapprovedpassword",
            is_approved=False,
            local_node=self.node,
        )
        AuthorProfile.objects.create(
            user=unapproved_user,
        )
        self.client.login(username="unapproved_user", password="unapprovedpassword")
        response = self.client.get(reverse("authorApp:friends_page"))
        # Should redirect to login
        self.assertRedirects(response, reverse("authorApp:login"))

    # Tests for follow_author
    def test_follow_author_send_request(self):
        """
        Test that an approved user can send a follow request to another user.
        """
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.post(
            reverse("authorApp:follow_author", args=[self.author_profile2.id])
        )
        # Should redirect back
        self.assertEqual(response.status_code, 302)
        # Check that a follow request was created
        self.assertTrue(
            Follower.objects.filter(
                actor=self.author_profile1, object=self.author_profile2
            ).exists()
        )
        follow_request = Follower.objects.get(
            actor=self.author_profile1, object=self.author_profile2
        )
        self.assertEqual(follow_request.status, "p")  # Pending

    def test_follow_author_self(self):
        """
        Test that a user cannot follow themselves.
        """
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.post(
            reverse("authorApp:follow_author", args=[self.author_profile1.id])
        )
        self.assertEqual(response.status_code, 302)
        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "You cannot follow or unfollow yourself." in str(message)
                for message in messages
            )
        )
        # Ensure no follow request was created
        self.assertFalse(
            Follower.objects.filter(
                actor=self.author_profile1, object=self.author_profile1
            ).exists()
        )

    # Tests for accept_follow_request
    def test_accept_follow_request(self):
        """
        Test that a user can accept a follow request.
        """
        # User2 sends a follow request to User1
        Follower.objects.create(
            actor=self.author_profile2,
            object=self.author_profile1,
            status="p",  # Pending
            created_by=self.author_profile2,
        )
        # User1 logs in and accepts the request
        self.client.login(username="testuser1", password="testpassword1")
        follow_request = Follower.objects.get(
            actor=self.author_profile2, object=self.author_profile1
        )
        response = self.client.post(
            reverse("authorApp:accept_follow_request", args=[follow_request.id])
        )
        self.assertEqual(response.status_code, 302)
        # Check that the request status is now 'a' (accepted)
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, "a")
        # Since mutual following doesn't exist yet, no friendship is created
        self.assertFalse(
            Friends.objects.filter(
                Q(user1=self.author_profile1, user2=self.author_profile2)
                | Q(user1=self.author_profile2, user2=self.author_profile1)
            ).exists()
        )

    def test_accept_follow_request_mutual_follow(self):
        """
        Test that a friendship is created when both users follow each other.
        """
        # User2 sends a follow request to User1
        Follower.objects.create(
            actor=self.author_profile2,
            object=self.author_profile1,
            status="p",  # Pending
            created_by=self.author_profile2,
        )
        # User1 already follows User2
        Follower.objects.create(
            actor=self.author_profile1,
            object=self.author_profile2,
            status="a",  # Accepted
            created_by=self.author_profile1,
        )
        # User1 logs in and accepts the request
        self.client.login(username="testuser1", password="testpassword1")
        follow_request = Follower.objects.get(
            actor=self.author_profile2, object=self.author_profile1
        )
        response = self.client.post(
            reverse("authorApp:accept_follow_request", args=[follow_request.id])
        )
        self.assertEqual(response.status_code, 302)
        # Check that the request status is now 'a' (accepted)
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, "a")
        # Check that friendship is established
        self.assertTrue(
            Friends.objects.filter(
                Q(user1=self.author_profile1, user2=self.author_profile2)
                | Q(user1=self.author_profile2, user2=self.author_profile1)
            ).exists()
        )

    # Tests for deny_follow_request
    def test_deny_follow_request(self):
        """
        Test that a user can deny a follow request.
        """
        # User2 sends a follow request to User1
        Follower.objects.create(
            actor=self.author_profile2,
            object=self.author_profile1,
            status="p",  # Pending
            created_by=self.author_profile2,
        )
        # User1 logs in and denies the request
        self.client.login(username="testuser1", password="testpassword1")
        follow_request = Follower.objects.get(
            actor=self.author_profile2, object=self.author_profile1
        )
        response = self.client.post(
            reverse("authorApp:deny_follow_request", args=[follow_request.id])
        )
        self.assertEqual(response.status_code, 302)
        # Check that the request status is now 'd' (denied)
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, "d")

    # Tests for unfriend
    def test_unfriend(self):
        """
        Test that a user can unfriend another user.
        """
        # Establish friendship
        # First, create mutual following
        Follower.objects.create(
            actor=self.author_profile1,
            object=self.author_profile2,
            status="a",
            created_by=self.author_profile1,
        )
        Follower.objects.create(
            actor=self.author_profile2,
            object=self.author_profile1,
            status="a",
            created_by=self.author_profile2,
        )
        # Create friendship
        user1, user2 = sorted(
            [self.author_profile1, self.author_profile2], key=lambda x: x.id
        )
        Friends.objects.create(
            user1=user1,
            user2=user2,
            created_by=self.author_profile1,
        )
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.post(
            reverse("authorApp:unfriend", args=[self.author_profile2.id])
        )
        self.assertEqual(response.status_code, 302)
        # Check that friendship is deleted
        self.assertFalse(
            Friends.objects.filter(
                Q(user1=self.author_profile1, user2=self.author_profile2)
                | Q(user1=self.author_profile2, user2=self.author_profile1)
            ).exists()
        )
        # Also check that the follow from user1 to user2 is deleted
        self.assertFalse(
            Follower.objects.filter(
                actor=self.author_profile1, object=self.author_profile2
            ).exists()
        )

    # Testing is_approved decorator
    def test_is_approved_decorator(self):
        """
        Test that the is_approved decorator redirects unapproved users.
        """
        # Create an unapproved user
        unapproved_user = User.objects.create_user(
            username="unapproved_user",
            password="unapprovedpassword",
            is_approved=False,
            local_node=self.node,
        )
        AuthorProfile.objects.create(
            user=unapproved_user,
        )
        self.client.login(username="unapproved_user", password="unapprovedpassword")
        response = self.client.get(reverse("authorApp:friends_page"))
        # Should redirect to login
        self.assertRedirects(response, reverse("authorApp:login"))


class AuthorAppTests(APITestCase):
    def setUp(self):
        # Create test users and profiles
        self.user1 = User.objects.create_user(
            username="author1", password="password1", display_name="Author One"
        )
        self.user2 = User.objects.create_user(
            username="author2", password="password2", display_name="Author Two"
        )
        self.node = Node.objects.create(
            url="http://localhost:8000", created_by=self.user1
        )

        self.user2.local_node = self.node
        self.user2.save()

        self.user1.local_node = self.node
        self.user1.save()

        # Create author profiles
        self.author1 = AuthorProfile.objects.create(user=self.user1)
        self.author2 = AuthorProfile.objects.create(user=self.user2)

        # Create friendships and followers with `created_by`
        Friends.objects.create(
            user1=self.author1, user2=self.author2, created_by=self.author1
        )
        Follower.objects.create(
            actor=self.author1, object=self.author2, status="a", created_by=self.author1
        )

        # Authenticate as user1
        self.client.login(username="author1", password="password1")

    def test_list_authors(self):
        """Test listing all authors"""
        url = reverse("authorApp:author-list")
        response = self.client.get(url)
        len_all = len(AuthorProfile.objects.all())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), len_all
        )  # Ensure some authors are returned

    def test_list_authors_pagination(self):
        """Test listing all authors with pagination"""
        page = 1
        size = 1
        url = reverse("authorApp:author-list")
        url = f"{url}?page={page}&size={size}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Ensure 1 author is returned

    def test_update_author(self):
        """Test updating a single author by username"""
        # Set up the URL for the author's detail endpoint
        url = reverse("authorApp:author-detail", args=[self.user1.username])

        # Define the data for updating the author
        updated_data = {
            "username": self.user1.username,  # Keep the same
            "displayName": "UpdatedFirstName",
        }

        # Send the PUT request with the updated data
        response = self.client.put(path=url, data=updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_author(self):
        """Test retrieving a single author by username"""
        url = reverse("authorApp:author-detail", args=[self.user1.username])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["displayName"], self.user1.display_name)

    def test_author_friends(self):
        """Test retrieving friends of an author"""
        url = reverse("authorApp:author-friends", args=[self.user1.username])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only one friend created in setup
        friend_data = response.data[0]
        self.assertTrue(
            (
                friend_data["user1"]["displayName"] == self.user1.display_name
                and friend_data["user2"]["displayName"] == self.user2.display_name
            )
            or (
                friend_data["user1"]["displayName"] == self.user2.display_name
                and friend_data["user2"]["displayName"] == self.user1.display_name
            )
        )
