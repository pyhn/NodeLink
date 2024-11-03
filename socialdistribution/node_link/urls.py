from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "node_link"

# Initialize the router
router = DefaultRouter()
router.register(r'nodes', views.NodeViewSet, basename='node')
router.register(r'notifications', views.NotificationViewSet, basename='notification')


urlpatterns = [
    path("<str:username>/", views.home, name="home"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("api/", include(router.urls)),  # Include router-generated API URLs
]
