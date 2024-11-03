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
    path("edit-profile/", views.edit_profile, name="edit_profile"),

]
