from django.urls import path
from . import views

app_name = "postApp"
urlpatterns = [
    path("create_post/", views.create_post, name="create_post"),
    path("posts_list/<int:post_id>/", views.post_detail, name="post_detail"),
    path("create_comment/<int:post_id>/", views.create_comment, name="create_comment"),
    path("like_post/<int:post_id>/", views.like_post, name="like_post"),
    path("post_card/<str:u_id>/", views.post_card, name="one_post"),
    path("delete_post/<int:post_id>/", views.delete_post, name="delete_post"),
]
