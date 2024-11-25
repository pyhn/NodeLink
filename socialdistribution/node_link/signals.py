# from https://docs.djangoproject.com/en/5.1/topics/signals/, Django Project, accessed 2024-10-19
# from OpenAI ChatGPT, (paraphrased) how do I use push-based model for notification along with signals, accessed 2024-10-19
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from node_link.models import Notification
from authorApp.models import Follower, User, AuthorProfile
from postApp.models import Post, Like
from django.db.models import Q, CharField
from django.db.models.functions import Cast


@receiver(post_save, sender=Post)
def notify_followers_on_new_post(sender, instance, created, **kwargs):
    if created:
        author = instance.author
        followers = Follower.objects.filter(object=author)
        for follower in followers:
            message = f"{author.user.username} has made a new post."
            link_url = reverse(
                "postApp:post_detail", args=[author.user.username, instance.uuid]
            )
            Notification.objects.create(
                user=follower.actor,
                message=message,
                notification_type="new_post",
                related_object_id=str(instance.id),
                author_picture_url=author.user.profileImage,
                link_url=link_url,
            )


@receiver(post_save, sender=Follower)
def notify_author_on_new_follow_request(sender, instance, created, **kwargs):
    print("follow request signal triggered")
    if created and instance.status == "p":
        print("Follow request created. notifying the followee")
        author = instance.actor
        target_author = instance.object
        message = f"{author.user.username} wants to follow you."
        Notification.objects.create(
            user=target_author,
            message=message,
            notification_type="pending_follow_request",
            related_object_id=str(instance.id),
            author_picture_url=author.user.profileImage,
            link_url=reverse("authorApp:profile_display", args=[author.user.username]),
        )
        print("notification created")


@receiver(post_save, sender=Follower)
def update_notification_on_follow_request_status_change(sender, instance, **kwargs):
    if instance.status == "a":
        Notification.objects.filter(
            notification_type="pending_follow_request",
            related_object_id=str(instance.id),
            user=instance.object,
        ).update(
            message=f"{instance.actor.user.username} is now following you.",
            notification_type="accepted_follow_request",
            author_picture_url=instance.actor.user.profileImage,
        )
    elif instance.status == "d":
        Notification.objects.filter(
            notification_type="pending_follow_request",
            related_object_id=str(instance.id),
            user=instance.object,
        ).update(
            message=f"You have denied the follow request from {instance.actor.user.username}.",
            notification_type="denied_follow_request",
            author_picture_url=instance.actor.user.profileImage,
        )


@receiver(pre_save, sender=User)
def update_notifications_on_profile_image_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    old_image = old_instance.profileImage
    new_image = instance.profileImage

    if old_image != new_image:
        author_profile = instance.author_profile

        # Update the author's own notifications
        Notification.objects.filter(user__user=instance).update(
            author_picture_url=new_image
        )

        # # Get follower IDs and cast them to strings in the database query
        # follower_ids = Follower.objects.filter(actor=author_profile).values_list(
        #     "id", flat=True
        # )

        # Cast the Follower IDs to CharField to match the TextField type
        follower_ids_str = (
            Follower.objects.filter(actor=author_profile)
            .annotate(id_str=Cast("id", output_field=CharField()))
            .values_list("id_str", flat=True)
        )

        # Update Notifications
        Notification.objects.filter(
            Q(notification_type="pending_follow_request")
            | Q(notification_type="accepted_follow_request")
            | Q(notification_type="denied_follow_request"),
            related_object_id__in=follower_ids_str,
        ).update(author_picture_url=new_image)


@receiver(post_save, sender=Like)
def notify_author_on_new_like(sender, instance, created, **kwargs):
    print("Like signal triggered")
    if created:
        post = instance.post
        author = instance.author
        if post.author != author:
            print("Like created, notifying author via notification")
            message = f"{author.user.username} liked your post."
            link_url = reverse(
                "postApp:post_detail", args=[author.user.username, post.uuid]
            )
            Notification.objects.create(
                user=post.author,  # Use post.author (AuthorProfile)
                message=message,
                notification_type="like",
                related_object_id=str(instance.id),
                author_picture_url=author.user.profileImage,
                link_url=link_url,
            )


@receiver(post_delete, sender=Like)
def delete_notifications_on_like_delete(sender, instance, **kwargs):
    Notification.objects.filter(
        notification_type="like",
        related_object_id=str(instance.id),
        user=instance.post.author,
    ).delete()


@receiver(post_delete, sender=Follower)
def delete_notifications_on_follower_delete(sender, instance, **kwargs):
    Notification.objects.filter(
        notification_type__in=[
            "follow_request",
            "accepted_follow_request",
            "denied_follow_request",
        ],
        related_object_id=str(instance.id),
        user=instance.object,
    ).delete()


@receiver(post_delete, sender=Post)
def delete_notifications_on_post_delete(sender, instance, **kwargs):
    Notification.objects.filter(
        notification_type="new_post",
        related_object_id=str(instance.id),
        user=instance.author,
    ).delete()
