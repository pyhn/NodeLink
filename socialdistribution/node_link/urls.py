from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("create_post/", views.create_post, name="create_post"),
    path('posts_list/', views.post_list, name='post_list'),
    path('posts_list/<int:id>/', views.post_detail, name='post_detail'),
]
