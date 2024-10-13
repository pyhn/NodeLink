from django.shortcuts import render, redirect, get_object_or_404
from .models import Post, Author, Admin, Node
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from .models import Post, Author, Admin, Node

# Create your views here.
def home(request):
    return render(request, "home.html")

  


def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content", "")
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

        # Access author's username
        author_username = new_post.author.username
        print(f"Post created by {author_username}")

        # Redirect to the post list page
        return redirect("post_list")  # Updated to redirect to 'post_list'

    return render(request, "create_post.html")


def post_list(request):
    # Retrieve all posts
    posts = Post.objects.all()
    return render(request, 'post_list.html', {'posts': posts})

def post_detail(request, id):
    # Retrieve the post by id
    post = get_object_or_404(Post, id=id)
    return render(request, 'post_detail.html', {'post': post})