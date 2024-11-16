import base64
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from .models import Node
from django.utils.deprecation import MiddlewareMixin


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
