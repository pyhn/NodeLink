import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
from node_link.models import Node


def extract_base_url(full_url):
    """
    Extracts the base URL from an author's URL.
    For example, given 'http://HerokuNodeA.com/api/authors/martinmj', it returns 'http://HerokuNodeA.com/'.
    """
    parsed_url = urlparse(full_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    return base_url


def send_to_remote_inbox(full_url, data):
    """
    Sends data to a remote author's inbox.
    - inbox_url: The full inbox URL of the remote author (e.g., 'http://remote-node.com/api/authors/456/inbox')
    - data: A dictionary containing the data to send (e.g., a post, comment, like, follow request)
    """
    remote_node_url = extract_base_url(full_url)
    try:
        remote_node = Node.objects.get(url=remote_node_url, is_active=True)
    except Node.DoesNotExist:
        # Handle error: remote node not found or inactive
        return False

    inbox_url = f"{full_url}/inbox"  # Adjust if API structure is different

    auth = HTTPBasicAuth(remote_node.username, remote_node.password)

    headers = {"Content-Type": "application/json"}

    response = requests.post(inbox_url, json=data, auth=auth, headers=headers)

    return response.status_code in [200, 201]
