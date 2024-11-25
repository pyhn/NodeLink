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


def send_to_remote_inboxes(json, author):
    """
    Send the post JSON object to the inbox of all remote users.

    Args:
        author(AuthorProfile): Author to send to
        json (dict): The post JSON object to send.
    """
    # Find all remote users (usernames containing '__')

    # Extract the remote author's username
    if not author.user.local_node.is_active:
        return

    # Construct the inbox URL
    inbox_url = f"{author.fqid}/inbox"
    local_node = Node.objects.filter(is_remote=False).first()
    # Send the POST request to the inbox
    try:
        if author.user.local_node and author.user.local_node.is_active:

            headers = {"X-original-host": local_node.url}
            response = requests.post(
                inbox_url,
                json=json,
                auth=(
                    author.user.local_node.username,
                    author.user.local_node.raw_password,
                ),
                timeout=10,
                headers=headers,
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            print(f"Successfully sent to {inbox_url}. Response: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send to {inbox_url}. Error: {str(e)}")
