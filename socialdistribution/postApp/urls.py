from django.urls import path
from . import views

app_name = "postApp"
urlpatterns = [
    path("create_post/", views.create_post, name="create_post"),
    path("posts_list/<uuid:post_uuid>/", views.post_detail, name="post_detail"),
    path(
        "create_comment/<uuid:post_uuid>/", views.create_comment, name="create_comment"
    ),
    path("like_post/<uuid:post_uuid>/", views.like_post, name="like_post"),
    path("post_card/<uuid:post_uuid>/", views.post_card, name="one_post"),
    path("delete_post/<uuid:post_uuid>/", views.delete_post, name="delete_post"),
    # API endpoints (ensure the links match -- check for trailing slashes refer to Posts API)
    # ://service/api/authors/{AUTHOR_SERIAL}/posts/{POST_SERIAL}
    path(
        "api/authors/<str:author_serial>/posts/<uuid:post_serial>",
        views.PostDetailAPIView.as_view(),
        name="post_detail_api",
    ),
    # ://service/api/authors/{AUTHOR_SERIAL}/posts
    path(
        "api/authors/<str:author_serial>/posts",
        views.PostListCreateAPIView.as_view(),
        name="post_list_create_api",
    ),
    # ://service/api/posts/{post_fqid}
    path(
        "api/posts/<path:post_fqid>",
        views.PostByFQIDAPIView.as_view(),
        name="post_by_fqid_api",
    ),
]
