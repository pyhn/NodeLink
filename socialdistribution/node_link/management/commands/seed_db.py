import logging
from random import choice, randint

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db.models import Q
from faker import Faker
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
                displayName=fake.name(),
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
        self.create_fake_friends(authors)
        logger.info("Friends created for Authors.")

        # Create fake followers
        logger.info("Creating fake followers...")
        self.create_fake_followers(authors)
        logger.info("Followers created for Authors.")

        logger.info("Fake data generation completed successfully.")
        logger.info(f"Sample Username: {authors[1]}")

    def create_fake_friends(self, authors):
        """
        Creates mutual friendships between authors.
        Each author will have up to 5 friends.
        """
        max_friends_per_author = 5
        for author in authors:
            # Determine how many friends to add for this author
            current_friend_count = Friends.objects.filter(
                Q(user1=author) | Q(user2=author)
            ).count()
            friends_to_add = randint(0, max_friends_per_author - current_friend_count)

            for _ in range(friends_to_add):
                potential_friend = choice(authors)
                if potential_friend == author:
                    continue  # Skip self

                # Ensure ordering to comply with unique constraint (user1_id < user2_id)
                if author.id < potential_friend.id:
                    user1, user2 = author, potential_friend
                else:
                    user1, user2 = potential_friend, author

                # Check if the friendship already exists
                if Friends.objects.filter(user1=user1, user2=user2).exists():
                    continue  # Friendship already exists

                # Create the friendship
                Friends.objects.create(user1=user1, user2=user2, created_by=user2)
                logger.debug(
                    f"Friendship created between {user1.user.username} and {user2.user.username}"
                )

    def create_fake_followers(self, authors):
        """
        Creates follow relationships between authors.
        Each author will have up to 2 followers.
        Ensures that followers are not already friends.
        """
        max_followers_per_author = 2
        for author in authors:
            # Determine how many followers to add for this author
            current_follower_count = Follower.objects.filter(
                object=author, status="a"
            ).count()
            followers_to_add = randint(
                0, max_followers_per_author - current_follower_count
            )

            for _ in range(followers_to_add):
                potential_follower = choice(authors)
                if potential_follower == author:
                    continue  # Skip self

                # Ensure that the follower is not already a friend
                # Check if a friendship exists between potential_follower and author
                if Friends.objects.filter(
                    Q(user1=potential_follower) | Q(user2=potential_follower),
                    Q(user1=author) | Q(user2=author),
                ).exists():
                    continue  # They are already friends

                # Check if the follower already follows the author
                if Follower.objects.filter(
                    actor=potential_follower, object=author
                ).exists():
                    continue  # Already follows

                # Create the follower with status 'A' (Accepted)
                Follower.objects.create(
                    actor=potential_follower,
                    object=author,
                    status="a",
                    created_by=potential_follower,  # Assuming 'created_by' is part of MixinApp
                )
                logger.debug(
                    f"{potential_follower.user.username} is now following {author.user.username}"
                )
