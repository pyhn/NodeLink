from datetime import datetime  # Standard library

import requests  # Third-party library

from django.contrib import admin  # Django imports
from django import forms
from django.contrib.auth.hashers import make_password
from django.contrib import messages

from .models import Node  # Project-specific imports
from authorApp.serializers import AuthorToUserSerializer


class NodeAdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = Node
        fields = ["url", "username", "password", "is_active"]

    def save(self, commit=True):
        node = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            node.password = make_password(raw_password)
        else:
            if node.pk:
                # Keep the existing password if not changed
                node.password = Node.objects.get(pk=node.pk).password
        if commit:
            node.save()
        return node


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    form = NodeAdminForm
    list_display = (
        "url",
        "username",
        "is_active",
        "created_by",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        try:
            api_url = f"{obj.url.rstrip('/')}/api/authors/"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors

            data = response.json()
            serializer = AuthorToUserSerializer(data=data)
            if serializer.is_valid():
                users = serializer.save()
                print(f"Successfully added {len(users)} authors from node {obj.url}.")
            else:
                print(
                    f"Failed to process authors from {obj.url}. Errors: {serializer.errors}"
                )

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to node {obj.url}. Details: {str(e)}")
