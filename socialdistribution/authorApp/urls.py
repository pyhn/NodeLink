from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "authorApp"  # namspace

# Initialize the router
router = DefaultRouter()
router.register(r'authors', views.AuthorProfileViewSet, basename='author')

# Define other URLs
urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("<str:author_un>/profile", views.profile_display, name="profile_display"),
]

# Include router URLs
urlpatterns += router.urls