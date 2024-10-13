from django.shortcuts import render, redirect
from .models import Post, Author, Admin, Node


# Create your views here.
def home(request):
    return render(request, "home.html")

  
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility")

        # Create or get a dummy admin
        admin, _ = Admin.objects.get_or_create(
            username="dummy_admin",
            defaults={
                'password': 'dummy_password',
                'email': 'dummy_admin@example.com'
            }
        )

        # Create or get a dummy node
        node, _ = Node.objects.get_or_create(
            url='http://dummy_node_url.com',
            defaults={
                'admin': admin,
                'created_by': admin,
                'updated_by': admin,
                'deleted_by': admin
            }
        )

        # Check if the user is authenticated and try to get the corresponding Author
        if request.user.is_authenticated:
            try:
                author = Author.objects.get(pk=request.user.pk)
            except Author.DoesNotExist:
                # If not, create an Author linked to the request.user
                author = Author.objects.create(
                    username=request.user.username,
                    password=request.user.password,
                    email=request.user.email,
                    local_node=node
                )
        else:
            # Create or get a dummy author
            author, _ = Author.objects.get_or_create(
                username="dummy_author",
                defaults={
                    'password': 'dummy_password',
                    'email': 'dummy_author@example.com',
                    'local_node': node
                }
            )

        # Create the post with the necessary fields
        new_post = Post.objects.create(
            title=title,
            content=content,
            img=img,
            visibility=visibility,
            author=author,
            node=node,
            created_by=author,
            updated_by=author
        )

        # Optional: Print the author's username for verification
        author_username = new_post.author.username
        print(f"Post created by {author_username}")

        # Redirect to a success page after creating the post
        return redirect("post_success")

    # Render the form template if the request method is not POST
    return render(request, "create_post.html")