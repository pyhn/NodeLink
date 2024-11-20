import requests
from node_link.models import Node
from authorApp.serializers import AuthorToUserSerializer


def fetch_remote_authors():
    """
    Periodically fetch the remote author by calling the remote node's author endpoint.
    """
    # get all ACTIVE and REMOTE nodes
    remote_nodes = Node.objects.filter(is_remote=True, is_active=True)

    # check if there are no remote nodes
    if not remote_nodes:
        print("No remote nodes found.")
        return

    print("fetching...")
    # loop through each one and fetch the authors
    for node in remote_nodes:
        # append authors api endpoint to the node's url
        authors_url = node.url.rstrip("/") + "/api/authors/"
        # auth that will be used to access the endpoint
        auth = (node.username, node.password)
        try:
            # now, try to send a request.get to the endpoint
            response = requests.get(authors_url, auth=auth, timeout=10)
            # check if the response is successful
            response.raise_for_status()
            # get the authors data from the response
            authors_data = response.json()
            print(authors_data)
            # use the sereializer to save the authors data
            serializer = AuthorToUserSerializer(data=authors_data, many=True)
            # check if the data is valid
            if serializer.is_valid():
                # save the authors data
                serializer.save()
                print(f"Fetched authors from {node.url}")
            else:
                print(f"Invalid data from {node.url}: {serializer.errors}")
        except requests.RequestException as e:
            print(f"Error fethcing authors from {node.url}: {e}")
