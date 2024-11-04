# Django Imports
from django.db import models

# Project Imports
from node_link.utils.mixin import MixinApp

# Package Imports
import uuid


class Post(MixinApp):
    visibility_choices = [
        ("p", "PUBLIC"),
        ("u", "UNLISTED"),
        ("fo", "FRIENDS "),
        ("d", "DELETED"),
    ]
    type_choices = [  #!!!API NOTE:
        ("a", "application/base64"),
        ("png", "image/png"),
        ("jpeg", "image/jpeg"),
        ("p", "text/plain"),
        ("m", "text/markdown"),
    ]
    title = models.TextField(default="New Post")
    description = models.TextField(default="")
    content = models.TextField(blank=True, default="")
    # img = models.ImageField(upload_to="images/", null=True) #!!!POST NOTE: save this in content field at dataurl
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    node = models.ForeignKey(
        "node_link.Node", on_delete=models.CASCADE, related_name="posts"
    )
    author = models.ForeignKey(
        "authorApp.AuthorProfile", on_delete=models.CASCADE, related_name="posts"
    )
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=True)
    contentType = models.CharField(
        max_length=10, choices=type_choices, default="p", blank=False, null=False
    )


class Comment(MixinApp):
    visibility_choices = [
        ("p", "public"),
        ("fo", "friends-only"),
    ]  #!!! POST NOTE !!!API NOTE is this necessary
    content = models.TextField(null=False, default="")
    visibility = models.CharField(max_length=2, choices=visibility_choices, default="p")
    post = models.ForeignKey(
        "postApp.Post", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        "authorApp.AuthorProfile", on_delete=models.CASCADE, related_name="comments"
    )
    # contentType = models.CharField(max_length=225, default="text/markdown")#!!! POST NOTE !!!API NOTE is this necessary
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return f"Comment by {self.author.user.display_name} on {self.post.title}"


class CommentLike(MixinApp):
    comment = models.ForeignKey(
        "postApp.Comment", on_delete=models.CASCADE, related_name="commentLiked"
    )
    author = models.ForeignKey(
        "authorApp.AuthorProfile", on_delete=models.CASCADE, related_name="likesComment"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["author", "comment"], name="unique_comment_like"
            )
        ]

    def __str__(self):
        return f"{self.author.user.display_name} liked '{self.comment}'"


class Like(MixinApp):
    post = models.ForeignKey(
        "postApp.Post", on_delete=models.CASCADE, related_name="postliked"
    )
    author = models.ForeignKey(
        "authorApp.AuthorProfile", on_delete=models.CASCADE, related_name="likesPost"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["author", "post"], name="unique_like")
        ]

    def __str__(self):
        return f"{self.author.user.username} liked '{self.post.title}'"
