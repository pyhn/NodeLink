# from OpenAI CHATGPT, (paraphrasing) can you test if a user can see a post based on the post's visibility?
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from authorApp.models import AuthorProfile, User, Friends
from postApp.models import Post, Comment, Like
from node_link.models import Node, Notification

from rest_framework.test import APIClient
from rest_framework import status

import tempfile
import uuid
import base64
from PIL import Image
import io


class PostAppViewsTestCase(TestCase):
    def setUp(self):
        # Step 1: Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            is_approved=True,
            display_name="Test User",
        )

        # Step 2: Create a test node, setting created_by to self.user
        self.node = Node.objects.create(url="http://testnode.com", created_by=self.user)

        # Step 3: Create a test author profile, setting local_node to self.node
        self.author_profile = AuthorProfile.objects.create(
            user=self.user, local_node=self.node
        )

        # Initialize the test client and log in
        self.client = Client()
        self.client.login(username="testuser", password="testpassword")

    def test_create_post_view_get(self):
        """
        Test that the create_post view renders the create_post.html template for a GET request.
        """
        response = self.client.get(reverse("postApp:create_post"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "create_post.html")

    def test_submit_post_view_post_text(self):
        """
        Test submitting a text post via the submit_post view.
        """
        post_data = {
            "title": "Test Post",
            "description": "Test Description",
            "content": "This is a test post content.",
            "visibility": "p",  # Public
            "contentType": "p",  # Plain text
        }
        response = self.client.post(reverse("postApp:submit_post"), data=post_data)
        self.assertEqual(
            response.status_code, 302
        )  # Should redirect after successful post
        self.assertRedirects(response, reverse("node_link:home"))
        # Verify that the post was created
        post_exists = Post.objects.filter(
            title="Test Post",
            author=self.author_profile,
            node=self.node,  # Ensure the node is correct
        ).exists()
        self.assertTrue(post_exists)

    def test_submit_post_view_post_image(self):
        """
        Test submitting an image post via the submit_post view.
        """
        # Create a simple image in memory
        image = Image.new("RGB", (100, 100), color="red")
        temp_image = io.BytesIO()
        image.save(temp_image, format="PNG")
        temp_image.seek(0)

        # Create an uploaded file object
        image_file = SimpleUploadedFile(
            "test_image.png", temp_image.read(), content_type="image/png"
        )

        post_data = {
            "title": "Test Image Post",
            "description": "Test Description",
            "visibility": "p",  # Public
            "contentType": "png",  # Image PNG
            "img": image_file,
        }
        response = self.client.post(reverse("postApp:submit_post"), data=post_data)
        self.assertEqual(
            response.status_code, 302
        )  # Should redirect after successful post
        self.assertRedirects(response, reverse("node_link:home"))
        # Verify that the post was created
        post = Post.objects.get(title="Test Image Post", author=self.author_profile)
        self.assertIsNotNone(post)
        self.assertTrue(post.content.startswith("data:image/png;base64,"))

    def test_submit_post_view_post_invalid_image(self):
        """
        Test submitting an image post with an invalid image file.
        """
        invalid_image_file = SimpleUploadedFile(
            "test.txt", b"not an image", content_type="text/plain"
        )
        post_data = {
            "title": "Test Invalid Image Post",
            "description": "Test Description",
            "visibility": "p",
            "contentType": "png",  # Image PNG
            "img": invalid_image_file,
        }
        response = self.client.post(reverse("postApp:submit_post"), data=post_data)
        # Should redirect back to create_post page due to invalid image
        self.assertRedirects(response, reverse("postApp:create_post"))

    def test_create_comment_view_post(self):
        """
        Test creating a comment on a post.
        """
        # First, create a test post
        post = Post.objects.create(
            title="Test Post",
            description="Test Description",
            content="Test Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        comment_data = {"content": "This is a test comment."}
        response = self.client.post(
            reverse("postApp:create_comment", args=[post.uuid]),
            data=comment_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",  # To simulate AJAX if necessary
        )
        self.assertEqual(response.status_code, 200)
        # Verify that the comment was created
        comment_exists = Comment.objects.filter(
            content="This is a test comment.", post=post, author=self.author_profile
        ).exists()
        self.assertTrue(comment_exists)

    def test_create_post_view_not_approved(self):
        """
        Test that a user who is not approved cannot access the create_post view.
        """
        # Log out and create a new unapproved user
        self.client.logout()
        unapproved_user = User.objects.create_user(
            username="unapproveduser",
            password="testpassword",
            is_approved=False,
            display_name="Unapproved User",
        )
        AuthorProfile.objects.create(user=unapproved_user, local_node=self.node)
        self.client.login(username="unapproveduser", password="testpassword")
        response = self.client.get(reverse("postApp:create_post"))
        self.assertEqual(
            response.status_code, 302
        )  # Should redirect due to is_approved decorator
        self.assertRedirects(response, reverse("authorApp:login"))

    def test_submit_post_view_get(self):
        """
        Test that a GET request to submit_post redirects to home.
        """
        response = self.client.get(reverse("postApp:submit_post"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("node_link:home"))

    def test_create_comment_view_post_invalid_post(self):
        """
        Test creating a comment on a non-existent post.
        """
        fake_uuid = uuid.uuid4()
        comment_data = {"content": "This is a test comment."}
        response = self.client.post(
            reverse("postApp:create_comment", args=[fake_uuid]), data=comment_data
        )
        self.assertEqual(response.status_code, 404)  # Post not found

    def test_create_comment_view_not_authenticated(self):
        """
        Test that an unauthenticated user cannot create a comment.
        """
        self.client.logout()
        post = Post.objects.create(
            title="Test Post",
            description="Test Description",
            content="Test Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        comment_data = {"content": "This is a test comment."}
        response = self.client.post(
            reverse("postApp:create_comment", args=[post.uuid]), data=comment_data
        )
        self.assertEqual(response.status_code, 302)
        # Should redirect to login page
        login_url = reverse("authorApp:login")  # Adjust based on your login URL
        expected_url = (
            f"{login_url}?next={reverse('postApp:create_comment', args=[post.uuid])}"
        )
        self.assertRedirects(response, expected_url)

    def test_like_post_view(self):
        """
        Test liking a post.
        """
        # Create a test post
        post = Post.objects.create(
            title="Test Post to Like",
            description="Test Description",
            content="Test Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.post(reverse("postApp:like_post", args=[post.uuid]))
        # Should redirect to the post detail page
        self.assertRedirects(response, reverse("postApp:post_detail", args=[post.uuid]))
        # Verify that the like was created
        like_exists = Like.objects.filter(
            post=post, author=self.author_profile
        ).exists()
        self.assertTrue(like_exists)

    def test_delete_post_view(self):
        """
        Test deleting a post.
        """
        # Create a test post
        post = Post.objects.create(
            title="Test Post to Delete",
            description="Test Description",
            content="Test Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.post(reverse("postApp:delete_post", args=[post.uuid]))
        # Should redirect to home
        self.assertRedirects(response, reverse("node_link:home"))
        # Verify that the post's visibility is set to 'd' (deleted)
        post.refresh_from_db()
        self.assertEqual(post.visibility, "d")

    def test_delete_post_view_not_author(self):
        """
        Test that a user cannot delete someone else's post.
        """
        # Create another user and author profile
        other_user = User.objects.create_user(
            username="otheruser",
            password="testpassword",
            is_approved=True,
            display_name="Other User",
        )
        other_author_profile = AuthorProfile.objects.create(
            user=other_user, local_node=self.node
        )
        # Create a post by the other user
        post = Post.objects.create(
            title="Other User Post",
            description="Test Description",
            content="Test Content",
            visibility="p",
            contentType="p",
            author=other_author_profile,
            node=self.node,
            created_by=other_author_profile,
            updated_by=other_author_profile,
        )
        response = self.client.post(reverse("postApp:delete_post", args=[post.uuid]))
        # Should redirect to home, but post should not be deleted
        self.assertRedirects(response, reverse("node_link:home"))
        # Verify that the post's visibility is still 'p'
        post.refresh_from_db()
        self.assertEqual(post.visibility, "p")

    def test_edit_post_view_get(self):
        """
        Test accessing the edit_post view for a post the user owns.
        """
        # Create a test post
        post = Post.objects.create(
            title="Post to Edit",
            description="Test Description",
            content="Original Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.get(reverse("postApp:edit_post", args=[post.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "edit_post.html")
        self.assertContains(response, post.title)

    def test_edit_post_view_get_not_author(self):
        """
        Test that a user cannot access the edit_post view for someone else's post.
        """
        # Create another user and author profile
        other_user = User.objects.create_user(
            username="otheruser",
            password="testpassword",
            is_approved=True,
            display_name="Other User",
        )
        other_author_profile = AuthorProfile.objects.create(
            user=other_user, local_node=self.node
        )
        # Create a post by the other user
        post = Post.objects.create(
            title="Other User Post",
            description="Test Description",
            content="Test Content",
            visibility="p",
            contentType="p",
            author=other_author_profile,
            node=self.node,
            created_by=other_author_profile,
            updated_by=other_author_profile,
        )
        response = self.client.get(reverse("postApp:edit_post", args=[post.uuid]))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_submit_edit_post_view_post(self):
        """
        Test submitting changes to a post.
        """
        # Create a test post
        post = Post.objects.create(
            title="Original Title",
            description="Original Description",
            content="Original Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        edit_data = {
            "title": "Edited Title",
            "description": "Edited Description",
            "content": "Edited Content",
            "visibility": "u",  # Unlisted
            "contentType": "p",  # Plain text
            "submit_type": "plain",  # From updated form
        }
        response = self.client.post(
            reverse("postApp:submit_edit_post", args=[post.uuid]), data=edit_data
        )
        # Should redirect to post detail page
        self.assertRedirects(response, reverse("postApp:post_detail", args=[post.uuid]))
        # Verify that the post was updated
        post.refresh_from_db()
        self.assertEqual(post.title, "Edited Title")
        self.assertEqual(post.description, "Edited Description")
        self.assertEqual(post.content, "Edited Content")
        self.assertEqual(post.visibility, "u")

    def test_submit_edit_post_view_post_image(self):
        """
        Test submitting changes to a post with a new image.
        """
        # Create a test post
        post = Post.objects.create(
            title="Original Title",
            description="Original Description",
            content="Original Content",
            visibility="p",
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        # Create a new image
        image = Image.new("RGB", (100, 100), color="blue")
        temp_image = io.BytesIO()
        image.save(temp_image, format="JPEG")
        temp_image.seek(0)
        image_file = SimpleUploadedFile(
            "new_image.jpg", temp_image.read(), content_type="image/jpeg"
        )

        edit_data = {
            "title": "Edited Title with Image",
            "description": "Edited Description",
            "visibility": "p",
            "contentType": "jpeg",
            "submit_type": "image",
            "img": image_file,
        }
        response = self.client.post(
            reverse("postApp:submit_edit_post", args=[post.uuid]), data=edit_data
        )
        # Should redirect to post detail page
        self.assertRedirects(response, reverse("postApp:post_detail", args=[post.uuid]))
        # Verify that the post was updated
        post.refresh_from_db()
        self.assertEqual(post.title, "Edited Title with Image")
        self.assertTrue(post.content.startswith("data:image/jpeg;base64,"))

    def test_post_card_view(self):
        """
        Test accessing the post_card view for a post the user has access to.
        """
        # Create a test post
        post = Post.objects.create(
            title="Test Post Card",
            description="Test Description",
            content="Test Content",
            visibility="p",  # Public
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.get(reverse("postApp:one_post", args=[post.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "post_card.html")
        self.assertContains(response, post.title)

    def test_post_card_view_no_access(self):
        """
        Test accessing the post_card view for a post the user does not have access to.
        """
        # Create a private post by another user
        other_user = User.objects.create_user(
            username="otheruser",
            password="testpassword",
            is_approved=True,
            display_name="Other User",
        )
        other_author_profile = AuthorProfile.objects.create(
            user=other_user, local_node=self.node
        )
        post = Post.objects.create(
            title="Private Post",
            description="Test Description",
            content="Test Content",
            visibility="fo",  # Friends-only
            contentType="p",
            author=other_author_profile,
            node=self.node,
            created_by=other_author_profile,
            updated_by=other_author_profile,
        )
        response = self.client.get(reverse("postApp:one_post", args=[post.uuid]))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_post_detail_view(self):
        """
        Test accessing the post_detail view for a post the user has access to.
        """
        # Create a test post with comments
        post = Post.objects.create(
            title="Test Post Detail",
            description="Test Description",
            content="Test Content",
            visibility="p",  # Public
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        # Create a comment
        Comment.objects.create(
            content="Test Comment",
            visibility="p",
            post=post,
            author=self.author_profile,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.get(reverse("postApp:post_detail", args=[post.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "post_details.html")
        self.assertContains(response, post.title)
        self.assertContains(response, "Test Comment")

    def test_render_share_form_view(self):
        """
        Test rendering the share post form.
        """
        # Create a public post
        post = Post.objects.create(
            title="Post to Share",
            description="Test Description",
            content="Test Content",
            visibility="p",  # Public
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.get(
            reverse("postApp:render_share_form", args=[self.user.username, post.uuid])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "share_post_form.html")
        self.assertContains(response, post.title)

    def test_render_share_form_view_non_public(self):
        """
        Test rendering the share post form for a non-public post.
        """
        # Create a friends-only post
        post = Post.objects.create(
            title="Non-Public Post",
            description="Test Description",
            content="Test Content",
            visibility="fo",  # Friends-only
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        response = self.client.get(
            reverse("postApp:render_share_form", args=[self.user.username, post.uuid])
        )
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_handle_share_post_view(self):
        """
        Test sharing a post with other authors.
        """
        # Create a public post
        post = Post.objects.create(
            title="Post to Share",
            description="Test Description",
            content="Test Content",
            visibility="p",  # Public
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        # Create another author to share with
        other_user = User.objects.create_user(
            username="otheruser",
            password="testpassword",
            is_approved=True,
            display_name="Other User",
        )
        other_author_profile = AuthorProfile.objects.create(
            user=other_user, local_node=self.node
        )
        share_data = {"recipients": [other_author_profile.id]}
        response = self.client.post(
            reverse("postApp:handle_share_post", args=[self.user.username, post.uuid]),
            data=share_data,
        )
        # Expect a JSON response indicating success
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True})
        # Verify that a notification was created
        notification_exists = Notification.objects.filter(
            user=other_author_profile,
            message__contains=f"{self.user.username} shared a post with you.",
            related_object_id=str(post.id),
        ).exists()
        self.assertTrue(notification_exists)

    def test_handle_share_post_view_non_public(self):
        """
        Test sharing a non-public post.
        """
        # Create a friends-only post
        post = Post.objects.create(
            title="Non-Public Post",
            description="Test Description",
            content="Test Content",
            visibility="fo",  # Friends-only
            contentType="p",
            author=self.author_profile,
            node=self.node,
            created_by=self.author_profile,
            updated_by=self.author_profile,
        )
        share_data = {"recipients": []}
        response = self.client.post(
            reverse("postApp:handle_share_post", args=[self.user.username, post.uuid]),
            data=share_data,
        )
        self.assertEqual(response.status_code, 403)  # Forbidden
