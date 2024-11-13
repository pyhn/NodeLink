import requests
from django.utils import timezone
from postApp.models import Post
from authorApp.models import AuthorProfile
import uuid

def fetch_github_events(request):
    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
    url = f"https://api.github.com/users/{author.get_github_username}/events"
    response = requests.get(url)
    if response.status_code == 200:
        events = response.json()
        for event in events:
            if event['type'] == 'PushEvent':
                repo_name = event['repo']['name']
                commit_message = event['payload']['commits'][0]['message']
                created_at = timezone.now()
                post_content = f"New GitHub push to {repo_name}: {commit_message}"
                
                # Create a new post
                Post.objects.create(
                    author=author,
                    title="New GitHub Activity",
                    description="Automatically generated from GitHub activity.",
                    content=post_content,
                    visibility="p",
                    node=author.local_node,
                    uuid=uuid.uuid4(),
                    contentType="p",
                    created_at=created_at
                )
    else:
        print(f"Failed to fetch events: {response.status_code}")
