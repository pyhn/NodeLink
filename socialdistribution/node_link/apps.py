from django.apps import AppConfig


class NodeLinkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "node_link"

    # from https://stackoverflow.com/questions/2719038/where-should-signal-handlers-live-in-a-django-project by mlissner and Aidan, Stack Overflow, accessed 20240-10-19
    def ready(self):
        print("Connecting signal handlers...")
        import node_link.signals  # Ensure signals are imported
