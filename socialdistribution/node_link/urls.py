from django.urls import path
from . import views

# app_name = "node_link"
urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("post_card/<str:u_id>/", views.post_card, name="one_post"),
    path("", views.home, name="home"),
    path("logout/", views.logout_view, name="logout"),
    path("create_post/", views.create_post, name="create_post"),
    path("posts_list/", views.post_list, name="post_list"),
    path("posts_list/<int:post_id>/", views.post_detail, name="post_detail"),
    path("create_comment/<int:post_id>/", views.create_comment, name="create_comment"),
    path("like_post/<int:post_id>/", views.like_post, name="like_post"),
    path("/<str:author_un>/profile", views.profile_display, name="profile_display"),
    path("notifications/", views.notifications_view, name="notifications"),
]
