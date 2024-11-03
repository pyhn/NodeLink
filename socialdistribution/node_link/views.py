# from django.shortcuts import render, HttpResponse


from django.shortcuts import render
from django.http import HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from node_link.models import Notification
from authorApp.models import Friends, Follower
from postApp.models import Post

# post edit/create methods


@login_required
def home(request):

    if request.method == "GET":
        template_name = "home.html"
        user = request.user.author_profile

        friends = list(
            Friends.objects.filter(Q(user1=user) | Q(user2=user)).values_list(
                "user1", "user2"
            )
        )
        friends = list(set(u_id for tup in friends for u_id in tup))
        following = list(
            Follower.objects.filter(Q(actor=user, status=True)).values_list(
                "object", flat=True
            )
        )

        # Get all posts
        all_posts = list(
            Post.objects.filter(
                Q(visibility="p")  # all public
                | Q(
                    visibility="fo",  # all friends only
                    author_id__in=friends,
                )
                | Q(
                    visibility="u",  # all unlisted
                    author_id__in=following,
                )
            )
            .distinct()
            .order_by("-updated_at")
            .values_list("uuid", flat=True)
        )

        context = {"all_ids": all_posts}

        # Return the rendered template
        return render(request, template_name, context)
    return HttpResponseNotAllowed("Invalid Method;go home")


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        user=request.user.author_profile
    ).order_by("-created_at")
    notifications.update(is_read=True)  # Mark notifications as read
    return render(request, "notifications.html", {"notifications": notifications})
