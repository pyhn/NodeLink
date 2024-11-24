import requests
from postApp.models import Post
from authorApp.models import AuthorProfile


def fetch_github_events(request):
    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
    
    # If user doesn't have GitHub username, just return
    if author.user.github_user is None:
        return []

    url = f"https://api.github.com/users/{author.user.github_user}/events"
    response = requests.get(url)
    
    # Ensure we got a successful response
    if response.status_code != 200:
        print(f"Error fetching GitHub events: {response.status_code}")
        return []
    
    # Load the JSON data from the response
    events = response.json()

    # If the response doesn't contain the expected list of events, return an empty list
    if not isinstance(events, list):
        print(f"Unexpected response format: {events}")
        return []

    # Reverse the events to prioritize the most recent events
    events.reverse()
    
    new_posts = []
    latest_event_id = None

    for event in events:
        event_id = event["id"]

        # Check if the event is new by comparing with last_github_event_id
        if author.last_github_event_id == event_id:
            break  # Stop if we've reached the most recent processed event

        repo_name = event["repo"]["name"]
        event_type = event["type"]
        post_content = f"New GitHub {event_type} in {repo_name}."

        if event_type == "PushEvent":
            commit_messages = [
                commit["message"] for commit in event["payload"]["commits"]
            ]
            post_content = f"New GitHub push to {repo_name}:\n" + "\n".join(
                commit_messages
            )

        elif event_type == "CreateEvent":
            ref_type = event["payload"].get("ref_type", "repository")
            ref = event["payload"].get("ref", repo_name)
            post_content = f"Created new {ref_type}: {ref} in {repo_name}."

        elif event_type == "PullRequestEvent":
            action = event["payload"]["action"]
            pr_title = event["payload"]["pull_request"]["title"]
            post_content = f"Pull request '{pr_title}' {action} in {repo_name}."

        elif event_type == "IssuesEvent":
            action = event["payload"]["action"]
            issue_title = event["payload"]["issue"]["title"]
            post_content = f"Issue '{issue_title}' {action} in {repo_name}."

        # Create a new post
        Post.objects.create(
            title="New GitHub Activity",
            description="Automatically generated from GitHub activity.",
            content=post_content,
            visibility="p",
            node=author.user.local_node,
            author=author,
            contentType="p",
            created_by=author,
        )
        new_posts.append(event_id)

        # Track the latest event ID to update after processing
        if latest_event_id is None:
            latest_event_id = event_id

    # Update last_github_event_id only if there were new events
    if new_posts:
        author.last_github_event_id = latest_event_id
        author.save()

    return new_posts