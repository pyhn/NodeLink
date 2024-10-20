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
    path("notifications/", views.notifications_view, name="notifications"),
    path("friends/", views.friends_page, name="friends_page"),
    path("follow/<int:author_id>/", views.follow_author_pyhn, name="follow_author"),
    path("follow_requests/", views.follow_requests_list, name="follow_requests_list"),
    path(
        "accept_request/<int:request_id>/",
        views.accept_follow_request_pyhn,
        name="accept_follow_request",
    ),
    path(
        "deny_request/<int:request_id>/",
        views.deny_follow_request_pyhn,
        name="deny_follow_request",
    ),
    path("unfriend/<int:friend_id>/", views.unfriend, name="unfriend"),
]
