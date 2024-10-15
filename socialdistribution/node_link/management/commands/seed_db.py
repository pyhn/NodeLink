import logging
from django.core.management.base import BaseCommand
from faker import Faker
from random import choice
from node_link.models import Author, Node, Post, Like, Comment, Admin
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

        admin = Admin.objects.create(
            username=fake.user_name(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            password=make_password("adminpassword123"),  # Set a default admin password
        )

        # Create a Node first (as Authors require it)
        node = Node.objects.create(
            admin=admin,  # Replace with an actual Admin instance if necessary
            url=fake.url(),
            created_by=admin,  # Replace with an actual Admin instance if necessary
            deleted_by=None,  # Replace with an actual Admin instance if necessary
        )
        logger.info("Node created.")

        # Create fake authors
        authors = []
        logger.info("Creating fake authors...")
        for _ in range(10):
            author = Author.objects.create(
                username=fake.user_name(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                password=make_password(
                    "password123"
                ),  # Set a default password for testing
                github_url=fake.url(),
                github_token=fake.sha1(),
                github_user=fake.user_name(),
                local_node=node,
            )
            authors.append(author)
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

        logger.info("Fake data generation completed successfully.")
