from django.db import models
from datetime import datetime
from django.contrib.auth.models import AbstractUser
import uuid

# We use abstract user if we want everything a base User has but want to add more fields (But also maintaining the way it is authenticated)
# ^from: https://docs.djangoproject.com/en/5.1/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project

# The user model already has attributes: username, first_name, last_name, email, password, date_joined
# we can remove all the previous redundant fields because we can still set them are were already defined by User
# ^ also has a custom set_password() method that takes in a raw password and auto hashes it
# ^ from: https://docs.djangoproject.com/en/5.1/ref/contrib/auth/#user-model


class User(AbstractUser):
    date_ob = models.DateField(null=True, blank=True)  # date of brith

    profile_image = models.ImageField(
        upload_to="profile_images/",
        null=True,
        blank=True,
        default="/static/icons/user_icon.svg",
    )
    # ^switched from filepathfield to ImageField
    # FilePathField only stores the path location of a file and can only be used if the file already exists in the system
    # ImageField is a file upload field (inherited from FileField) but validates the uploaded object is a valid image
    # ^from: https://docs.djangoproject.com/en/5.1/ref/models/fields/#django.db.models.ImageField

    display_name = models.CharField(max_length=50, null=True, blank=True)
    # ^username is unique and required for log in / user set up
    # ^display_name is optional and works as display names in instagram (can be the same as other people)
    # ^(we don't need to implement if we don't want to and just have everyone as unique)

    description = models.TextField(null=True, blank=True)  # profile bio

    def __str__(self):
        return str(self.display_name) or str(self.username)


class Node(models.Model):

    url = models.TextField(null=False)
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_nodes"
    )
    updated_at = models.DateTimeField(default=datetime.now)
    deleted_at = models.DateTimeField(default=datetime.now)
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="deleted_nodes",
    )


class AuthorProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="author_profile"
    )
    github_url = models.CharField(max_length=255, null=True, blank=True)
    github_token = models.CharField(max_length=255, null=True, blank=True)
    github_user = models.CharField(max_length=255, null=True, blank=True)
    local_node = models.ForeignKey("Node", on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.user.username} (Author)"


class MixinApp(models.Model):
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        AuthorProfile, on_delete=models.PROTECT, related_name="%(class)s_created"
    )

    updated_at = models.DateTimeField(default=datetime.now, null=True, blank=True)

    updated_by = models.ForeignKey(
        AuthorProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(class)s_updated",
    )

    deleted_at = models.DateTimeField(default=datetime.now, null=True, blank=True)

    class Meta:
        abstract = True


class Post(MixinApp):
    visibility_choices = [
        ("p", "public"),
        ("u", "unlisted"),
        ("fo", "friends-only"),
        ("d", "deleted"),
    ]
    title = models.TextField(default="New Post")
    content = models.TextField(blank=True, default="")
    img = models.ImageField(upload_to="images/", null=True)
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name="posts")
    author = models.ForeignKey(
        AuthorProfile, on_delete=models.PROTECT, related_name="posts"
    )
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    is_commonmark = models.BooleanField(default=False)


class Comment(MixinApp):
    visibility_choices = [("p", "public"), ("fo", "friends-only")]
    content = models.TextField(null=False, default="")
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        AuthorProfile, on_delete=models.PROTECT, related_name="comments"
    )

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class Like(MixinApp):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    author = models.ForeignKey(
        AuthorProfile, on_delete=models.CASCADE, related_name="likes"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["author", "post"], name="unique_like")
        ]

    def __str__(self):
        return f"{self.author.username} liked '{self.post.title}'"


class Friends(MixinApp):
    user1 = models.ForeignKey(
        AuthorProfile, on_delete=models.CASCADE, related_name="friendships_initiated"
    )
    user2 = models.ForeignKey(
        AuthorProfile, on_delete=models.CASCADE, related_name="friendships_received"
    )
    status = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_friendship")
        ]


class Follower(MixinApp):
    user1 = models.ForeignKey(
        AuthorProfile, on_delete=models.CASCADE, related_name="followers_initiated"
    )
    user2 = models.ForeignKey(
        AuthorProfile, on_delete=models.CASCADE, related_name="followers_received"
    )
    status = models.CharField(max_length=20, default="pending")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_follower")
        ]


class Notification(models.Model):
    user = models.ForeignKey(
        AuthorProfile, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    # notifications can be a follow_request, new post, etc.
    notification_type = models.CharField(max_length=20)
    # id of the related object
    related_object_id = models.CharField(max_length=255, null=True, blank=True)
    # url to the author's profile picture
    author_picture_url = models.URLField(null=True, blank=True)
    # message for follow request notifications
    follow_request_message = models.TextField(null=True, blank=True)
    link_url = models.URLField(null=True, blank=True)  # url to the related object

    def __str__(self):
        return f"{self.user.user.username} - {self.message}"
