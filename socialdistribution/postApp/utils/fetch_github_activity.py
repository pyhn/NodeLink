import requests
from postApp.models import Post
from authorApp.models import AuthorProfile
import uuid

def fetch_github_events(request):
    author = AuthorProfile.objects.get(pk=request.user.author_profile.pk)
    print(author.github_user)
    url = f"https://api.github.com/users/{author.github_user}/events"
    response = requests.get(url)
    events = response.json()
    for event in events:
        repo_name = event['repo']['name']
        commit_message = event['payload']['commits'][0]['message']
        post_content = f"New GitHub push to {repo_name}: {commit_message}"
                
        # # Create a new post
        # Post.objects.create(
        #     title="New GitHub Activity",
        #     description="Automatically generated from GitHub activity.",
        #     content=post_content,
        #     visibility="p",
        #     node=author.local_node,
        #     author=author,
        #     created_by=author,
        #     contentType="p",
        # )
