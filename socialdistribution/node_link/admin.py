from django.contrib import admin
from .models import Node, Post, Comment, Like, Notification

admin.site.register(Node)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Notification)
