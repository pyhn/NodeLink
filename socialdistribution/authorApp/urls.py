# Django Imports
from django.urls import path

# Project Imports
from . import views

app_name = "authorApp"
urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("<str:author_un>/profile", views.profile_display, name="profile_display"),
    path("friends/", views.friends_page, name="friends_page"),
    path("follow/<int:author_id>/", views.follow_author, name="follow_author"),
    path(
        "accept_request/<int:request_id>/",
        views.accept_follow_request,
        name="accept_follow_request",
    ),
    path(
        "deny_request/<int:request_id>/",
        views.deny_follow_request,
        name="deny_follow_request",
    ),
    path("unfriend/<int:friend_id>/", views.unfriend, name="unfriend"),
]
