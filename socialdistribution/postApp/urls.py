from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from . import views

app_name = "postApp"

# Initialize the router without registering the viewsets directly
router = DefaultRouter()

# Define urlpatterns for both API and regular views
urlpatterns = [
    # Simple identifier-based paths
    path("<str:username>/create_post/", views.create_post, name="create_post"),
    path("<str:username>/submit_post/", views.submit_post, name="submit_post"),
    path(
        "<str:username>/posts_list/<uuid:post_uuid>/",
        views.post_detail,
        name="post_detail",
    ),
    path(
        "<str:username>/create_comment/<uuid:post_uuid>/",
        views.create_comment,
        name="create_comment",
    ),
    path(
        "<str:username>/like_post/<uuid:post_uuid>/", views.like_post, name="like_post"
    ),
    path(
        "<str:username>/post_card/<uuid:post_uuid>/", views.post_card, name="one_post"
    ),
    path(
        "<str:username>/delete_post/<uuid:post_uuid>/",
        views.delete_post,
        name="delete_post",
    ),
    path(
        "<str:username>/edit_post/<uuid:post_uuid>/", views.edit_post, name="edit_post"
    ),
    path(
        "<str:username>/submit_edit_post/<uuid:post_uuid>/",
        views.submit_edit_post,
        name="submit_edit_post",
    ),
    # Sharing endpoints
    path(
        "share/<str:author_serial>/<uuid:post_uuid>/form/",
        views.render_share_form,
        name="render_share_form",
    ),
    path(
        "share/<str:author_serial>/<uuid:post_uuid>/",
        views.handle_share_post,
        name="handle_share_post",
    ),
    # Author and post-specific API endpoints (simple paths)
    path(
        "api/authors/<str:author_serial>/posts/",
        views.PostViewSet.as_view({"get": "list", "post": "create"}),
        name="author-posts",
    ),
    path(
        "api/posts/<uuid:uuid>/",
        views.LocalPostViewSet.as_view({"get": "list"}),
        name="local_author_post",
    ),
    path(
        "api/authors/<str:author_serial>/posts/<uuid:uuid>/",
        views.PostViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="author-post-detail",
    ),
    # Image endpoints
    path(
        "api/authors/<str:author_serial>/posts/<uuid:post_uuid>/image/",
        views.PostImageView.as_view(),
        name="post-image",
    ),
    path(
        "api/authors/<str:author_serial>/posts/<uuid:post_uuid>/likes/",
        views.PostLikesAPIView.as_view(),
        name="post-likes",
    ),
    path(
        "api/authors/<str:author_serial>/commented/",
        views.CommentedView.as_view(),
        name="author-commented",
    ),
    path(
        "api/authors/<str:author_serial>/commented/<uuid:comment_serial>/",
        views.CommentedView.as_view(),
        name="author-comment-detail",
    ),
    # FQID-based endpoints (specific regex)
    re_path(
        r"^api/authors/(?P<author_fqid>https?://[^/]+/.+)/commented/$",
        views.CommentedFQIDView.as_view(),
        name="author-commented-fqid",
    ),
    re_path(
        r"^api/authors/(?P<author_fqid>https?://[^/]+/.+)/liked/$",
        views.ThingsLikedByAuthorFQIDView.as_view(),
        name="things-liked-by-author-fqid",
    ),
    re_path(
        r"^api/liked/(?P<like_fqid>https?://[^/]+/.+)/$",
        views.SingleLikeFQIDView.as_view(),
        name="single-like-fqid",
    ),
    re_path(
        r"^api/authors/(?P<author_serial>[^/]+)/posts/(?P<post_serial>[^/]+)/comments/(?P<comment_fqid>https?://[^/]+/.+)/likes/$",
        views.CommentLikesView.as_view(),
        name="comment-likes",
    ),
    re_path(
        r"^api/posts/(?P<post_fqid>https?://[^/]+/.+)/likes/$",
        views.PostLikesFQIDAPIView.as_view(),
        name="post-likes-fqid",
    ),
    re_path(
        r"^api/commented/(?P<comment_fqid>https?://[^/]+/.+)/$",
        views.SingleCommentedView.as_view(),
        name="comment-detail",
    ),
    re_path(
        r"^api/posts/(?P<post_fqid>https?://[^/]+/.+)/comments/$",
        views.PostCommentsViewFQID.as_view(),
        name="post-comments-fqid",
    ),
    re_path(
        r"^api/authors/(?P<author_serial>[^/]+)/post/(?P<post_serial>[^/]+)/comment/(?P<remote_comment_fqid>https?://[^/]+/.+)/$",
        views.RemoteCommentView.as_view(),
        name="remote-comment-detail",
    ),
    re_path(
        r"^api/posts/(?P<post_fqid>https?://[^/]+/.+)/image/$",
        views.PostImageViewFQID.as_view(),
        name="post-detail-image",
    ),
    re_path(
        r"^api/posts/(?P<post_fqid>https?://[^/]+/.+)/$",
        views.SinglePostView.as_view(),
        name="post-detail",
    ),
]
