from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "postApp"

# Initialize the router and register the ViewSets
router = DefaultRouter()
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'comments', views.CommentViewSet, basename='comment')
router.register(r'likes', views.LikeViewSet, basename='like')

# Define urlpatterns for both API and regular views
urlpatterns = [
    # Regular view paths
    path("create_post/", views.create_post, name="create_post"),
    path("posts_list/<uuid:post_uuid>/", views.post_detail, name="post_detail"),
    path("create_comment/<uuid:post_uuid>/", views.create_comment, name="create_comment"),
    path("like_post/<uuid:post_uuid>/", views.like_post, name="like_post"),
    path("post_card/<uuid:post_uuid>/", views.post_card, name="one_post"),
    path("delete_post/<uuid:post_uuid>/", views.delete_post, name="delete_post"),

    # Include router URLs for ViewSets
    path("api/", include(router.urls)),  # This provides paths for posts, comments, and likes ViewSets
]
