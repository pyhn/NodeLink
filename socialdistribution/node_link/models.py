from django.db import models
from datetime import datetime
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    first_name = models.CharField(max_length=20, null=False)
    last_name = models.CharField(max_length=20, null=False)
    date_ob = models.DateField(null=False)
    profile_img = models.FilePathField(null=True)
    screen_name = models.CharField(max_length=20, null=False)
    description = models.TextField(null=False)
    join_date = models.DateField(null=False, default=datetime.now)
    email = models.EmailField(max_length=20, null=False, unique=True)


class Admin(User):
    def __str__(self):
        return f"{self.user.username} (Node Admin)"


class Node(models.Model):
    admin = models.ForeignKey(
        Admin, on_delete=models.PROTECT, related_name="managed_nodes"
    )
    url = models.TextField(null=False)
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        Admin, on_delete=models.PROTECT, related_name="created_nodes"
    )
    updated_at = models.DateTimeField(default=datetime.now)
    deleted_at = models.DateTimeField(default=datetime.now)
    deleted_by = models.ForeignKey(
        Admin, on_delete=models.PROTECT, related_name="deleted_nodes"
    )


class Author(User):
    github_url = models.CharField(null=True, max_length=255)
    github_token = models.CharField(null=True, max_length=255)
    github_user = models.CharField(null=True, max_length=255)
    local_node = models.ForeignKey(Node, null=False, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.user.username} (Author)"


class MixinApp(models.Model):
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        Author, on_delete=models.PROTECT, related_name="%(class)s_created"
    )
    updated_at = models.DateTimeField(default=datetime.now)
    updated_by = models.ForeignKey(
        Author, on_delete=models.PROTECT, related_name="%(class)s_updated"
    )
    deleted_at = models.DateTimeField(default=datetime.now)

    class Meta:
        abstract = True


class Post(MixinApp):
    visibility_choices = {"p": "public", "u": "unlisted", "fo": "friends-only"}
    content = models.TextField(null=True)
    img = models.ImageField(upload_to="images/", null=True)
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name="posts")


class Comment(MixinApp):
    visibility_choices = {"p": "public", "fo": "friends-only"}
    content = models.TextField(null=True)
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")


class Like(MixinApp):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["created_by", "post"], name="unique_like")
        ]


class Friends(MixinApp):
    user1 = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="friendships_initiated"
    )
    user2 = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="friendships_received"
    )
    status = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_friendship")
        ]


class Follower(MixinApp):
    user1 = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="followers_initiated"
    )
    user2 = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="followers_received"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_follower")
        ]
