# from https://docs.djangoproject.com/en/5.1/topics/signals/, Django Project, accessed 2024-10-19
# from OpenAI ChatGPT, (paraphrased) how do I use push-based model for notification along with signals, accessed 2024-10-19
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from node_link.models import Notification
from authorApp.models import Follower
from postApp.models import Post, Comment, Like, CommentLike


@receiver(post_save, sender=Post)
def notify_followers_on_new_post(sender, instance, created, **kwargs):
    if created:
        author = instance.author
        followers = Follower.objects.filter(
            object=author
        )  #!!!FRIENDS NOTE: Please double check
        for follower in followers:
            message = f"{author.user.username} has made a new post."
            link_url = reverse(
                "postApp:post_detail", args=[instance.uuid, author.user.username]
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
            user=target_author,  # Use target_author (AuthorProfile)
            message=message,
            notification_type="pending_follow_request",
            related_object_id=str(instance.id),
            # author_picture_url=author.user.profile_image,
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
        )
    elif instance.status == "d":
        Notification.objects.filter(
            notification_type="pending_follow_request",
            related_object_id=str(instance.id),
            user=instance.object,
        ).update(
            message=f"You have denied the follow request from {instance.actor.user.username}.",
            notification_type="denied_follow_request",
        )


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
                "postApp:post_detail", args=[post.uuid, author.user.username]
            )
            Notification.objects.create(
                user=post.author,  # Use post.author (AuthorProfile)
                message=message,
                notification_type="like",
                related_object_id=str(post.id),
                author_picture_url=author.user.profileImage,
                link_url=link_url,
            )


@receiver(post_delete, sender=Like)
def delete_notifications_on_like_delete(sender, instance, **kwargs):
    Notification.objects.filter(
        notification_type="like",
        related_object_id=str(instance.post.id),
        user=instance.post.author,
    ).delete()


@receiver(post_delete, sender=Follower)
def delete_notifications_on_follower_delete(sender, instance, **kwargs):
    Notification.objects.filter(
        notification_type="follow_request",
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
