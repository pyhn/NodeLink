import base64
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from .models import Node
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class RemoteNodeAuthBackend(BaseBackend):
    """
    The RemoteNodeAuthBackend uses the Node model to authenticate incoming requests from remote nodes based on the stored credentials.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header:
            return None

        if not auth_header.startswith("Basic "):
            return None

        try:
            encoded_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
        except (IndexError, ValueError, base64.binascii.Error):
            return None

        # Authenticate the node using the username and password
        try:
            local_node = Node.objects.get(username=username, is_active=True)
            if local_node.check_password(password):
                return local_node  # Return the node instance
        except Node.DoesNotExist:
            return None

        return None


class NodeBasicAuthentication(BaseAuthentication):
    """
    Custom Basic Authentication that validates requests against the Node model.
    """

    def authenticate(self, request):
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Basic "):
            return None  # No authentication provided

        try:
            # Decode the Base64 credentials
            encoded_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
        except (IndexError, ValueError, base64.binascii.Error) as exc:
            # Explicitly re-raise with context
            raise AuthenticationFailed("Invalid Basic Authentication header.") from exc

        # Authenticate the node
        try:
            node = Node.objects.get(username=username, is_active=True)
        except Node.DoesNotExist as exc:
            # Explicitly re-raise with context
            raise AuthenticationFailed("Node not found or inactive.") from exc
        if not node.check_password(password):
            raise AuthenticationFailed("Invalid username or password :P.")

        if not node.is_active:
            raise AuthenticationFailed("This node has been inactivated temporarily")

        # Return the authenticated node and None as the auth (no token here)
        return (node, None)

    def authenticate_header(self, request):
        return 'Basic realm="api"'
