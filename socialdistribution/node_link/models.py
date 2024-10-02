from django.db import models
from datetime import datetime


class Admin(models.Model):
    first_name = models.CharField(max_length=20, null=False)
    last_name = models.CharField(max_length=20, null=False)
    date_ob = models.DateField(null=False)
    profile_img = models.FilePathField(null=True)
    screen_name = models.CharField(max_length=20, null=False)
    description = models.TextField(null=False)
    join_date = models.DateField(null=False, default=datetime.now())
    email = models.CharField(max_length=20, null=False)


class Node(models.Model):
    admin = models.ForeignKey(Admin)
    url = models.TextField(null=False)
    created_at = models.DateField(default=datetime.now)
    created_by = models.ForeignKey(Admin)
    updated_at = models.DateField(default=datetime.now)
    deleted_at = models.DateField(default=datetime.now)
    deleted_by = models.ForeignKey(Admin)


class Author(models.Model):
    first_name = models.CharField(max_length=20, null=False)
    last_name = models.CharField(max_length=20, null=False)
    date_ob = models.DateField(null=False)
    profile_img = models.FilePathField(null=True)
    screen_name = models.CharField(max_length=20, null=False)
    description = models.TextField(null=False)
    join_date = models.DateField(null=False, default=datetime.now())
    email = models.CharField(max_length=20, null=False)
    github_url = models.CharField(null=True)
    github_token = models.CharField(null=True)
    github_user = models.CharField(null=True)
    local_node = models.ForeignKey(Node, null=False)


class MixinApp(models.Model):
    created_at = models.DateField(default=datetime.now)
    created_by = models.ForeignKey(Author)
    updated_at = models.DateField(default=datetime.now)
    updated_by = models.ForeignKey(Author)
    deleted_at = models.DateField(default=datetime.now)

    class Meta:
        abstract = True


class Post(MixinApp):
    visibility_choices = {"p": "public", "u": "unlisted", "fo": "friends-only"}
    content = models.TextField(null=True)
    img = models.FilePathField(null=True)
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    node = models.ForeignKey(Node)


class Comment(MixinApp):
    visibility_choices = {"p": "public", "fo": "friends-only"}
    content = models.TextField(null=True)
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    post = models.ForeignKey(Post)


class Like(MixinApp):
    post = models.ForeignKey(Post)


class Friends(MixinApp):
    user1 = models.ForeignKey(Author)
    user2 = models.ForeignKey(Author)
    status = models.BooleanField(default=False)


class Follower(MixinApp):
    user1 = models.ForeignKey(Author)
    user2 = models.ForeignKey(Author)
