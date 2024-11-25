import requests
from node_link.models import Node
from authorApp.serializers import AuthorProfileSerializer, AuthorToUserSerializer


def fetch_remote_authors():
    """
    Periodically fetch the remote author by calling the remote node's author endpoint.
    """
    # get all ACTIVE and REMOTE nodes
    remote_nodes = Node.objects.filter(is_remote=True, is_active=True)
    local_node = Node.objects.filter(is_remote=False).first()
    # check if there are no remote nodes
    if not remote_nodes:
        print("No remote nodes found.")
        return

    # Log existing remote nodes
    print("Existing Remote Nodes in Database:")
    for node in remote_nodes:
        print(f"- {node.url} (Active: {node.is_active})")

    # Retrieve the local node's URL
    try:
        local_node = Node.objects.get(is_remote=False, is_active=True)
        local_host = local_node.url.rstrip("/")
    except Node.DoesNotExist:
        print("Local node not found.")
        return

    print("fetching...")
    # loop through each one and fetch the authors
    for node in remote_nodes:
        # append authors api endpoint to the node's url
        authors_url = node.url.rstrip("/") + "/authors/"
        # Basic Authentication requires the raw password to authenticate with the remote server.
        auth = (node.username, node.raw_password)
        try:
            headers = {"X-original-host": local_node.url}
            # now, try to send a request.get to the endpoint
            response = requests.get(authors_url, auth=auth, timeout=10, headers=headers)
            # check if the response is successful
            response.raise_for_status()
            # get the authors data from the response
            authors_data = response.json()
            print(authors_data)
            authors_list = authors_data.get("authors", [])
        except requests.RequestException as e:
            print(f"Error fethcing authors from {authors_url}: {e}")
            continue
        except ValueError as e:
            print(f"Invalid JSON resonse from {authors_url}: {e}")
            continue

        # process each author in the list and see if the node they belong is active
        for author_data in authors_list:
            host = author_data.get("host")
            if not host:
                print(f"Author data missing 'host: {author_data}")
                continue  # skip this author and continue with the next one

            # Skip authors that belong to the local node
            if host.rstrip("/") == local_host:
                print(f"Skipping local author '{author_data.get('displayName')}'.")
                continue

            # see if that associated node is active
            try:
                Node.objects.get(url=host, is_remote=True, is_active=True)
            except Node.DoesNotExist:
                print(
                    f"Associated node for author '{author_data.get('displayName')}' is not active: {host} or DNE"
                )
                continue  # skip this author

            # use the sereializer to save the authors data
            serializer = AuthorProfileSerializer(data=author_data)
            if serializer.is_valid():
                serializer.save()
                print(
                    f"Imported author {author_data.get('displayName')} from {node.url}"
                )
            else:
                print(f"Invalid data for author from {node.url}: {serializer.errors}")