from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "node_link"

# Initialize the router
router = DefaultRouter()

urlpatterns = [
    path("notifications/", views.notifications_view, name="notifications"),
    path("<str:username>/", views.home, name="home"),
    # author-specific inbox
]
