from django.db import models
from datetime import datetime
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from authorApp.models import AuthorProfile, User


class Node(models.Model):

    url = models.TextField(null=False)
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "authorApp.User", on_delete=models.CASCADE, related_name="created_nodes"
    )
    updated_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(auto_now_add=True)
    deleted_by = models.ForeignKey(
        "authorApp.User",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="deleted_nodes",
    )
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save(update_fields=['password'])

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def save(self, *args, **kwargs):
        if not self.password.startswith('pbkdf2_') and self.password != '':
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url


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
