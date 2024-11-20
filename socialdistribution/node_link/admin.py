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

        if not change:
            # get the current site's URL from the request (this is basically our local node)
            current_site_url = request.scheme + "://" + request.get_host()
            print(current_site_url)

            # only when the url of the object != current_site_url (local url) will we fetch authors
            # otherwise, when we add our local node, it will fetch to itself which will be empty since
            # no authors can be made when there is no node. This will take uncessary HTTP
            if obj.url.rstrip("/") != current_site_url.rstrip("/"):
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
            else:
                # skip fetching authors for local node
                print("Local node detected. Skipping author fetch.")

                # print password (just curious)
                raw_password = form.cleaned_data.get(
                    "password"
                )  # Retrieve the local raw password
                print(f"Local node's password{raw_password}")
