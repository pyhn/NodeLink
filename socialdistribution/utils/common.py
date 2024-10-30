from django.shortcuts import get_object_or_404
from authorApp.models import Friends
from django.db.models import Q


def has_access(request, post_id):
    post = get_object_or_404(Post, id=post_id)  #!!!SPLIT
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
