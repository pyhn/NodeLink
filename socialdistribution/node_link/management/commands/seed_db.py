import logging
from django.core.management.base import BaseCommand
from faker import Faker
from random import choice
from node_link.models import (
    User,
    AdminProfile,
    AuthorProfile,
    Node,
    Post,
    Like,
    Comment,
    Friends,
    Follower,
)
from django.contrib.auth.hashers import make_password

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

        admin_profile = AdminProfile.objects.create(user=admin_user)

        # Create a Node first (as Authors require it)
        node = Node.objects.create(
            admin=admin_profile,
            url=fake.url(),
            created_by=admin_profile,
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
            )
            author_profile = AuthorProfile.objects.create(
                user=user,
                github_url=fake.url(),
                github_token=fake.sha1(),
                github_user=fake.user_name(),
                local_node=node,
            )
            authors.append(author_profile)
        logger.info(f"{len(authors)} fake authors created.")

        # Create fake posts
        logger.info("Creating fake posts...")
        posts = []
        for _ in range(20):
            aut = choice(authors)
            post = Post.objects.create(
                title=fake.sentence(),
                content=fake.paragraph(),
                img=None,  # Optional: Use if you have images to upload
                visibility=choice(["p", "u", "fo"]),
                node=node,
                author=aut,
                created_by=aut,
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
        for post in posts:
            for _ in range(5):  # Each post will get 5 comments
                author = choice(authors)
                Comment.objects.create(
                    content=fake.sentence(),
                    visibility=choice(["p", "fo"]),
                    post=post,
                    author=author,  # Randomly assign an author to the comment
                    created_by=author,
                )
        logger.info("Comments created for posts.")
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
            for _ in range(2):  # Each author will get 2 followers
                user1 = choice(authors)  # does not ensure they are not friends
                if (
                    user1 != author
                    and not Friends.objects.filter(user1=user1, user2=author).exists()
                ):
                    Friends.objects.create(
                        user1=user1,
                        user2=author,
                        created_by=author,
                    )
        logger.info("Followers created for Authors.")

        logger.info("Fake data generation completed successfully.")
