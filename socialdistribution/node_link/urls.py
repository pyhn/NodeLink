from django.urls import path
from . import views

# app_name = "node_link"
urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("post_card/<str:e_id>/", views.post_card, name="one_post"),
    path("", views.Home.as_view(), name="home"),
    path("logout/", views.logout_view, name="logout"),
]
