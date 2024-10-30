# Django Imports
from django.contrib import admin

# Project Imports
from .models import User, AuthorProfile, Friends, Follower

admin.site.register(User)
admin.site.register(AuthorProfile)
admin.site.register(Friends)
admin.site.register(Follower)
