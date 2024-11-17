# node_link/middleware.py
from node_link.models import Node
from django.contrib.auth import logout


class ClearNodeAuthMiddleware:
    """
    Middleware to clear Node authentication after the request is processed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Check if the request is for an API and a Node was authenticated
        if getattr(request, "is_api", False) and isinstance(request.user, Node):
            logout(request)  # Clears session and user auth state
            request.auth = None

        return response
