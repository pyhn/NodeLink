# Django Imports
from django.contrib import admin

# Project Imports
from .models import Post, Comment, CommentLike, Like

# Registering models with the admin site
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(CommentLike)
admin.site.register(Like)
