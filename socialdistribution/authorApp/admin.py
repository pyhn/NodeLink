# Django Imports
from django.contrib import admin

# Project Imports
from .models import User, AuthorProfile, Friends, Follower

admin.site.register(AuthorProfile)
admin.site.register(Friends)
admin.site.register(Follower)


class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "is_approved"]
    actions = ["approve_users"]
    list_filter = [
        "is_approved",
    ]  # Add the custom filter

    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)

    approve_users.short_description = "Approve selected users"


admin.site.register(User, UserAdmin)
