from django.shortcuts import render, HttpResponse
from django.shortcuts import render, redirect
from .models import Post, Author


# Create your views here.
def home(request):
    return render(request, "home.html")

  
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility")
        
        # Assuming the logged-in user is an Author and stored in request.user
        author = request.user  # request.user should be an instance of Author

        # Create a new post
        new_post = Post.objects.create(
            title=title,
            content=content,
            img=img,
            visibility=visibility,
            author=author,
            node=author.local_node  # Associate the post with the author's node
        )

        # Access author's username
        author_username = new_post.author.username
        print(f"Post created by {author_username}")

        return redirect("post_success")  # Redirect after successful post creation

    return render(request, "create_post.html")