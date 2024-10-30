from django.urls import path
from . import views

# app_name = "node_link"
urlpatterns = [
    path("", views.home, name="home"),
    path("notifications/", views.notifications_view, name="notifications"),
]
