from django.core.management.base import BaseCommand
from node_link.utils.fetch_remote_authors import fetch_remote_authors


class Command(BaseCommand):
    help = "Called to fetch authors from remote nodes (done via python manage.py fetch_remote_authors)"

    def handle(self, *args, **kwargs):
        """
        handler that will run the fetch.
        """
        # call the function that actually runs the fetch (socialdistribution/node_link/utils/fetch_remote_authors.py)
        fetch_remote_authors()
        self.stdout.write("Finished calling fetched_remote_authors.")
