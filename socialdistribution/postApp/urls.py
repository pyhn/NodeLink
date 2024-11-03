from django.urls import path
from . import views

app_name = "postApp"
urlpatterns = [
    path("create_post/", views.create_post, name="create_post"),
    path("submit_post/", views.submit_post, name="submit_post"),
    path("posts_list/<uuid:post_uuid>/", views.post_detail, name="post_detail"),
    path(
        "create_comment/<uuid:post_uuid>/", views.create_comment, name="create_comment"
    ),
    path("like_post/<uuid:post_uuid>/", views.like_post, name="like_post"),
    path("post_card/<uuid:post_uuid>/", views.post_card, name="one_post"),
    path("delete_post/<uuid:post_uuid>/", views.delete_post, name="delete_post"),
    path("edit_post/<uuid:post_uuid>/", views.edit_post, name="edit_post"),
    path(
        "submit_edit_post/<uuid:post_uuid>/",
        views.submit_edit_post,
        name="submit_edit_post",
    ),
]
