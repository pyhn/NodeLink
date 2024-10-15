from django.shortcuts import render, redirect, get_object_or_404
from .models import Post, Author, Admin, Node
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from .models import Post, Author, Admin, Node, Comment, Like
from django.shortcuts import render, redirect
from .models import Post, Author, Admin, Node
import uuid  # If using uuid for unique dummy usernames
  
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages


# Create your views here.
def home(request):
    return render(request, "home.html")

def get_or_create_dummy_node():
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

    return node

def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title", "New Post")
        content = request.POST.get("content", "")
        img = request.FILES.get("img", None)
        visibility = request.POST.get("visibility", "p")

        # Check if the user is authenticated
        if request.user.is_authenticated:
            try:
                # Try to get the Author associated with the logged-in user
                author = Author.objects.get(pk=request.user.pk)
            except Author.DoesNotExist:
                # Create an Author linked to the request.user
                author = Author.objects.create(
                    username=request.user.username,
                    password='dummy_password',
                    email=request.user.email,
                    local_node=get_or_create_dummy_node()
                )
        else:
            # Create or get a dummy author
            author, _ = Author.objects.get_or_create(
                username="dummy_author",
                defaults={
                    'password': 'dummy_password',
                    'email': 'dummy_author@example.com',
                    'local_node': get_or_create_dummy_node()
                }
            )

        # Create the post with the necessary fields
        new_post = Post.objects.create(
            title=title,
            content=content,
            img=img,
            visibility=visibility,
            author=author,
            node=author.local_node,  # Associate the post with the author's node
            created_by=author,
            updated_by=author
        )

        # Redirect to the post list page
        return redirect("post_list")

    return render(request, "create_post.html")


def post_list(request):
    # Retrieve all posts
    posts = Post.objects.all()
    return render(request, 'post_list.html', {'posts': posts})

def post_detail(request, id):
    post = get_object_or_404(Post, id=id)

    # Use a dummy author
    author, _ = Author.objects.get_or_create(
        username="dummy_author",
        defaults={
            'password': 'dummy_password',
            'email': 'dummy_author@example.com',
            'local_node': get_or_create_dummy_node()
        }
    )

    # Check if the dummy author has liked the post
    user_has_liked = post.likes.filter(author=author).exists()

    return render(request, 'post_detail.html', {
        'post': post,
        'user_has_liked': user_has_liked,
    })


def create_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        content = request.POST.get("content")

        # Check if the user is authenticated
        if request.user.is_authenticated:
            try:
                # Try to get the Author associated with the logged-in user
                author = Author.objects.get(pk=request.user.pk)
            except Author.DoesNotExist:
                # Create an Author linked to the request.user
                author = Author.objects.create(
                    username=request.user.username,
                    password='dummy_password',
                    email=request.user.email,
                    local_node=get_or_create_dummy_node()
                )
        else:
            # Create or get a dummy author
            author, _ = Author.objects.get_or_create(
                username="dummy_author",
                defaults={
                    'password': 'dummy_password',
                    'email': 'dummy_author@example.com',
                    'local_node': get_or_create_dummy_node()
                }
            )

        # Create the comment
        new_comment = Comment.objects.create(
            content=content,
            visibility='p',
            post=post,
            author=author,
            created_by=author,
            updated_by=author
        )

        # Redirect back to the post detail page
        return redirect('post_detail', id=post.id)

    return render(request, 'create_comment.html', {'post': post})

def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Use a dummy author
    author, _ = Author.objects.get_or_create(
        username="dummy_author",
        defaults={
            'password': 'dummy_password',
            'email': 'dummy_author@example.com',
            'local_node': get_or_create_dummy_node()
        }
    )

    # Check if the dummy author has already liked the post
    existing_like = Like.objects.filter(post=post, author=author)
    if existing_like.exists():
        existing_like.delete()
    else:
        Like.objects.create(
            post=post,
            author=author,          # Include the author field
            created_by=author,
            updated_by=author
        )

    return redirect('post_detail', id=post.id)
# def home(request):
#     return render(request, "home.html")

def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        password_confirm = request.POST['password_confirm']
        
        if password == password_confirm:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken')
            else:
                user = User.objects.create_user(username=username, password=password)
                user.save()
                messages.success(request, 'Account created successfully')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')

    return render(request, 'signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            
    return render(request, 'login.html')

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'home.html')

def logout_view(request):
    logout(request)
    return redirect('login')
