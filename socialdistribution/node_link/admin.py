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

    def clean_password(self):
        """
        Override the clean_password method to store the raw password.
        """
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            self.cleaned_data["_raw_password"] = raw_password
        return raw_password

    def save(self, commit=True):
        node = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            node.password = make_password(raw_password)
        else:
            if node.pk:
                # Keep the existing password if not changed
                existing_node = Node.objects.get(pk=node.pk)
                node.password = existing_node.password
                node.raw_password = existing_node.raw_password
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
        "is_remote",
        "created_by",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("is_remote", "created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user

        # get the current local url
        current_site_url = request.scheme + "://" + request.get_host()
        print(current_site_url)

        # set "is_remote" attribute based on URL comparison
        if obj.url.rstrip("/") != current_site_url.rstrip("/"):
            obj.is_remote = True
        else:
            # by default it is false since it is local
            obj.is_remote = False

        # save the object
        super().save_model(request, obj, form, change)

        # fetch remote authors if it is a new remote node
        if obj.is_remote and not change:
            # Fetch authors after remote node is created
            authors_url = obj.url.rstrip("/") + "/api/authors/"  # Ensure single '/'
            raw_password = form.cleaned_data.get(
                "_raw_password"
            )  # Retrieve the raw password
            if not raw_password:
                print("Password not provided. Cannot fetch authors.")
                return

            auth = (obj.username, raw_password)

            try:
                response = requests.get(authors_url, auth=auth, timeout=10)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                authors_data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch authors from {authors_url}: {e}")
                return
            except ValueError as e:
                print(f"Invalid JSON response from {authors_url}: {e}")
                return

            # Validate and save authors using the AuthorToUserSerializer
            serializer = AuthorToUserSerializer(data=authors_data)
            if serializer.is_valid():

                users = serializer.save()
                print(f"Successfully added {len(users)} authors from {obj.url}.")

            else:
                print(f"Invalid data from {authors_url}: {serializer.errors}")
