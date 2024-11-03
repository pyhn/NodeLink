# Django Imports
from django.db import models
from django.contrib.auth.models import AbstractUser

# Project Imports
from node_link.utils.mixin import MixinApp


class User(AbstractUser):
    date_ob = models.DateField(null=True, blank=True)

    profileImage = models.ImageField(  #!!!IMAGE NOTE: change to a url
        upload_to="profile_images/",
        null=True,
        blank=True,
        default="/static/icons/user_icon.svg",
    )

    display_name = models.CharField(max_length=50, null=False, blank=False)
    github_user = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)  # profile bio

    def __str__(self):
        return str(self.display_name) or str(self.username)


class AuthorProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="author_profile"
    )
    #!!!API NOTE:when making the API please make the 'id' url via f-strings and user.username or AuthorProfile.pk
    #!!!API NOTE:when making the API please make the 'host' url via f-strings and AuthorProfile.local_node.url
    #!!!API NOTE: type will have to be hardcoded
    github = models.CharField(max_length=255, null=True, blank=True)
    github_token = models.CharField(max_length=255, null=True, blank=True)
    github_user = models.CharField(max_length=255, null=True, blank=True)
    local_node = models.ForeignKey("node_link.Node", on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.user.username} (Author)"


class Friends(MixinApp):
    user1 = models.ForeignKey(
        "authorApp.AuthorProfile",
        on_delete=models.CASCADE,
        related_name="friendships_initiated",
    )
    user2 = models.ForeignKey(
        "authorApp.AuthorProfile",
        on_delete=models.CASCADE,
        related_name="friendships_received",
    )
    status = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_friendship")
        ]


class Follower(MixinApp):
    #!!!API NOTE: type will have to be hardcoded bc this info is for Followers and Follow Request API objs

    actor = models.ForeignKey(
        "authorApp.AuthorProfile",
        on_delete=models.CASCADE,
        related_name="followers_initiated",
    )
    object = models.ForeignKey(
        "authorApp.AuthorProfile",
        on_delete=models.CASCADE,
        related_name="followers_received",
    )

    status = models.CharField(max_length=20, default="pending")
    # API NOTE: Summary might be best done in the serializer bc its not used anywhere else and the data is readily available
    #!!!API NOTE, !!!FRIENDS NOTE there is no friends API, so we can check if (actor = 1, object = 2) and (actor = 2, object = 1) then create a Friend object after doing a API request
    # 1. user1(actor local) sends Follow Request to user2(object remote)
    # 2. create Follower obj (locally or API)
    # 3. If user2 approves then make Followers status=True(FIND OUT THROUGH Followers API for remote users)
    # 4. then user2 sends Follow Request
    # 5. Ask for Followers API for user1
    # 6. If user1 approves then make Friends obj (FIND OUT THROUGH Local query API for local users)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["actor", "object"], name="unique_follower")
        ]
