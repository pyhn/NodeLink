# from https://docs.djangoproject.com/en/5.1/topics/signals/, Django Project, accessed 2024-10-19
# from OpenAI ChatGPT, (paraphrased) how do I use push-based model for notification along with signals, accessed 2024-10-19
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from node_link.models import Post, Like, Comment, Follower, Notification


@receiver(post_save, sender=Post)
def notify_followers_on_new_post(sender, instance, created, **kwargs):
    if created:
        author = instance.author
        followers = Follower.objects.filter(user2=author)
        for follower in followers:
            message = f"{author.user.username} has made a new post."
            link_url = reverse("post_detail", args=[instance.id])
            Notification.objects.create(
                user=follower.user1,  # Use follower.user1 (AuthorProfile)
                message=message,
                notification_type="new_post",
                related_object_id=str(instance.id),
                author_picture_url=author.user.profile_image.url,
                link_url=link_url,
            )


@receiver(post_save, sender=Follower)
def notify_author_on_new_follow_request(sender, instance, created, **kwargs):
    if created and instance.status == "pending":
        author = instance.user1
        target_author = instance.user2
        message = f"{author.user.username} wants to follow you."
        link_url = reverse("approve_follow_request", args=[instance.id])
        Notification.objects.create(
            user=target_author,  # Use target_author (AuthorProfile)
            message=message,
            notification_type="follow_request",
            related_object_id=str(instance.id),
            author_picture_url=author.user.profile_image.url,
            follow_request_message=instance.follow_request_message,
            link_url=link_url,
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
            link_url = reverse("post_detail", args=[post.id])
            Notification.objects.create(
                user=post.author,  # Use post.author (AuthorProfile)
                message=message,
                notification_type="like",
                related_object_id=str(post.id),
                author_picture_url=author.user.profile_image,
                link_url=link_url,
            )
