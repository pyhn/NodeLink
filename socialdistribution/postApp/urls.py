from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "postApp"

# Initialize the router without registering the viewsets directly
router = DefaultRouter()

# Define urlpatterns for both API and regular views
urlpatterns = [
    # Regular view paths
    path("create_post/", views.create_post, name="create_post"),
    path("posts_list/<uuid:post_uuid>/", views.post_detail, name="post_detail"),
    path("create_comment/<uuid:post_uuid>/", views.create_comment, name="create_comment"),
    path("like_post/<uuid:post_uuid>/", views.like_post, name="like_post"),
    path("post_card/<uuid:post_uuid>/", views.post_card, name="one_post"),
    path("delete_post/<uuid:post_uuid>/", views.delete_post, name="delete_post"),


    path("api/authors/<str:author_serial>/posts/", views.PostViewSet.as_view({'get': 'list', 'post': 'create'}),
         name="author-posts"),
    path("api/authors/<str:author_serial>/posts/<uuid:uuid>/", views.PostViewSet.as_view(
        {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name="author-post-detail"),

    path("api/authors/<str:author_serial>/comments/", views.CommentViewSet.as_view({'get': 'list', 'post': 'create'}),
         name="author-comments"),
    path("api/authors/<str:author_serial>/comments/<uuid:uuid>/", views.CommentViewSet.as_view(
        {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name="author-comment-detail"),

    path("api/authors/<str:author_serial>/likes/", views.LikeViewSet.as_view({'get': 'list', 'post': 'create'}),
         name="author-likes"),
    path("api/authors/<str:author_serial>/likes/<uuid:uuid>/", views.LikeViewSet.as_view(
        {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
         name="author-like-detail"),

    # Include router URLs for other ViewSets if needed
    path("api/", include(router.urls)),
]
