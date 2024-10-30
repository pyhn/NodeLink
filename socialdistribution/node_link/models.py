from django.db import models
from datetime import datetime
from authorApp.models import AuthorProfile


class Node(models.Model):

    url = models.TextField(null=False)
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        "authorApp.User", on_delete=models.PROTECT, related_name="created_nodes"
    )
    updated_at = models.DateTimeField(default=datetime.now)
    deleted_at = models.DateTimeField(default=datetime.now)
    deleted_by = models.ForeignKey(
        "authorApp.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="deleted_nodes",
    )


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
