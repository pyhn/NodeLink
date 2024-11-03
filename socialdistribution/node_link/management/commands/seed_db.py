import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from faker import Faker
from random import choice
from node_link.models import Node

from postApp.models import Post, Comment, Like, CommentLike
from authorApp.models import Follower, Friends, AuthorProfile, User

# Set up logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generates fake data for Authors, Posts, Likes, and Comments"

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Logging the start of data generation
        logger.info("Starting to generate fake data...")

        logger.info("Creating fake Admin...")

        admin_user = User.objects.create(
            username=fake.user_name(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            password=make_password("adminpassword123"),
            is_staff=True,
            is_superuser=True,
        )

        # Create a Node first (as Authors require it)
        node = Node.objects.create(
            url=fake.url(),
            created_by=admin_user,
            deleted_by=None,  # Can be None if not deleted
        )

        # Create fake authors
        authors = []
        logger.info("Creating fake authors...")
        for _ in range(10):
            user = User.objects.create(
                username=fake.user_name(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                password=make_password("password123"),
                date_ob=fake.date(),  # Optional: set a random date of birth
                display_name=fake.name(),
            )
            author_profile = AuthorProfile.objects.create(
                user=user,
                github=fake.url(),
                github_token=fake.sha1(),
                github_user=fake.user_name(),
                local_node=node,
            )
            authors.append(author_profile)
        logger.info(f"{len(authors)} fake authors created.")

        # Create fake posts
        logger.info("Creating fake posts...")
        posts = []
        for _ in range(50):
            aut = choice(authors)
            post = Post.objects.create(
                title=fake.sentence(),
                description=fake.sentence(),
                content=fake.paragraph(),
                visibility=choice(["p", "u", "fo", "d"]),
                node=node,
                author=aut,
                created_by=aut,
                contentType=choice(["a", "png", "jpeg", "p", "m"]),
            )
            posts.append(post)
        logger.info(f"{len(posts)} fake posts created.")

        # Create fake likes
        logger.info("Creating fake likes...")
        for post in posts:
            for _ in range(3):  # Each post will get 3 likes
                author = choice(authors)
                Like.objects.get_or_create(post=post, author=author, created_by=author)
        logger.info("Likes created for posts.")

        # Create fake comments
        logger.info("Creating fake comments...")
        comments = []
        for post in posts:
            for _ in range(5):  # Each post will get 5 comments
                author = choice(authors)
                comment = Comment.objects.create(
                    content=fake.sentence(),
                    visibility=choice(["p", "fo"]),
                    post=post,
                    author=author,  # Randomly assign an author to the comment
                    created_by=author,
                )
                comments.append(comment)
        logger.info("Comments created for posts.")

        # Create fake Comment likes
        logger.info("Creating fake Comment likes...")
        for comment in comments:
            for _ in range(3):  # Each Comment will get 3 likes
                author = choice(authors)
                CommentLike.objects.get_or_create(
                    comment=comment, author=author, created_by=author
                )
        logger.info("Likes created for posts.")

        # Create fake friends
        logger.info("Creating fake friends...")
        for author in authors:
            for _ in range(5):  # Each author will get 5 friends
                user2 = choice(authors)
                if (
                    user2 != author
                    and not Friends.objects.filter(user1=author, user2=user2).exists()
                ):
                    Friends.objects.create(
                        user1=author,
                        status=choice([True, False]),
                        user2=user2,
                        created_by=author,
                    )
        logger.info("Friends created for Authors.")
        logger.info("Creating fake followers...")
        for author in authors:
            for _ in range(3):  # Each author will get 2 followers
                user1 = choice(authors)  # does not ensure they are not friends
                if (
                    user1 != author
                    and not Follower.objects.filter(actor=user1, object=author).exists()
                ):
                    Follower.objects.create(
                        actor=user1,
                        object=author,
                        created_by=author,
                        status=choice([True, False]),
                    )
        logger.info("Followers created for Authors.")

        logger.info("Fake data generation completed successfully.")
        logger.info(f"Sample Username: {authors[1]}")
