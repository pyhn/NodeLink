import requests
from node_link.models import Node
from authorApp.serializers import AuthorProfileSerializer


def fetch_remote_authors():
    """
    Periodically fetch the remote authors by calling the remote node's author endpoint.
    Starts with the initial endpoint and loops through paginated results.
    """
    # Get all ACTIVE and REMOTE nodes
    remote_nodes = Node.objects.filter(is_remote=True, is_active=True)
    local_node = Node.objects.filter(is_remote=False).first()

    if not remote_nodes:
        print("No remote nodes found.")
        return

    # Retrieve the local node's URL
    try:
        local_node = Node.objects.get(is_remote=False, is_active=True)
        local_host = local_node.url.rstrip("/")
    except Node.DoesNotExist:
        print("Local node not found.")
        return

    print("Fetching authors from remote nodes...")

    # Loop through each remote node and fetch authors
    for node in remote_nodes:
        authors_url = node.url.rstrip("/") + "/authors/"
        auth = (node.username, node.raw_password)
        headers = {"X-original-host": local_node.url}

        # First fetch from `api/authors/` (without `?page`)
        try:
            response = requests.get(authors_url, auth=auth, timeout=10, headers=headers)
            response.raise_for_status()
            authors_data = response.json()
            authors_list = authors_data.get("authors", [])

            # Process authors from the first response
            print(f"Processing authors from {authors_url}...")
            process_authors(authors_list, local_host, node)

        except requests.RequestException as e:
            print(f"Error fetching authors from {authors_url}: {e}")
            continue
        except ValueError as e:
            print(f"Invalid JSON response from {authors_url}: {e}")
            continue

        # Continue fetching remaining pages
        page = 2
        size = 10  # Adjust size if needed

        while True:
            try:
                params = {"page": page, "size": size}
                response = requests.get(
                    authors_url, auth=auth, timeout=10, headers=headers, params=params
                )
                response.raise_for_status()
                authors_data = response.json()

                # Extract authors list from the response
                authors_list = authors_data.get("authors", [])
                if not authors_list:
                    print(f"No more authors to fetch from {authors_url} (page {page}).")
                    break  # Exit loop if no authors are found

                print(f"Processing page {page} from {authors_url}...")
                process_authors(authors_list, local_host, node)

                page += 1  # Move to the next page

            except requests.RequestException as e:
                print(f"Error fetching authors from {authors_url} (page {page}): {e}")
                break
            except ValueError as e:
                print(f"Invalid JSON response from {authors_url} (page {page}): {e}")
                break

    print("Fetching authors completed.")


def process_authors(authors_list, local_host, node):
    """
    Process and save the authors from the response.
    """
    for author_data in authors_list:
        host = author_data.get("host")
        if not host:
            print(f"Author data missing 'host': {author_data}")
            continue

        # Skip authors that belong to the local node
        if host.rstrip("/") == local_host:
            print(f"Skipping local author '{author_data.get('displayName')}'.")
            continue

        # Ensure the associated node is active
        try:
            Node.objects.get(url=host, is_remote=True, is_active=True)
        except Node.DoesNotExist:
            print(
                f"Associated node for author '{author_data.get('displayName')}' is not active: {host} or does not exist."
            )
            continue

        # Save the author data using the serializer
        serializer = AuthorProfileSerializer(data=author_data)
        if serializer.is_valid():
            serializer.save()
            print(
                f"Imported author '{author_data.get('displayName')}' from {node.url}."
            )
        else:
            print(f"Invalid data for author from {node.url}: {serializer.errors}")
