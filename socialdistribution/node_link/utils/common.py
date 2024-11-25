# Django Imports
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib import messages
from django.urls import reverse
from rest_framework.pagination import PageNumberPagination

# Project Imports
from authorApp.models import Friends, User
from postApp.models import Post

import re


def has_access(request, post_uuid, username):

    post = get_object_or_404(Post, uuid=post_uuid)

    if (
        post.author.id == request.user.author_profile.id
        or post.visibility == "p"
        or post.visibility == "u"
        or (
            post.visibility == "fo"
            and Friends.objects.filter(
                Q(user1=request.user.author_profile, user2=post.author)
                | Q(user2=request.user.author_profile, user1=post.author)
            ).exists()
        )
    ) and not post.visibility == "d":
        return True
    return False


def is_approved(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_approved:
            return view_func(request, *args, **kwargs)
        messages.warning(
            request, "Your account is not approved. Please contact an admin for access."
        )

        return HttpResponseRedirect(reverse("authorApp:login"))

    return _wrapped_view


class CustomPaginator(PageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "size"


def remove_api_suffix(url):
    """
    Removes the 'api/' suffix from a URL if it ends with it.

    Args:
        url (str): The URL to process.

    Returns:
        str: The URL without the 'api/' suffix, or the original URL if the suffix is not present.
    """
    if url.endswith("api/"):
        return re.sub(r"/api/$", "", url)  # Remove the trailing 'api/' if present
    return url
