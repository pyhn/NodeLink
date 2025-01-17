from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from . import views

app_name = "postApp"

# Initialize the router without registering the viewsets directly
router = DefaultRouter()

# Define urlpatterns for both API and regular views
urlpatterns = [
    # Regular view paths
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
    # paths for sharing render and handle
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
    # Include router URLs for other ViewSets if needed
    path("api/", include(router.urls)),
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
    # List all comments by author or add a comment to a post
    path(
        "api/authors/<str:author_serial>/commented/",
        views.CommentedView.as_view(),
        name="author-commented",
    ),
    # Retrieve a specific comment made by an author (local/remote)
    path(
        "api/authors/<str:author_serial>/commented/<uuid:comment_serial>/",
        views.CommentedView.as_view(),
        name="author-comment-detail",
    ),
    re_path(
        r"^api/authors/(?P<author_fqid>.+)/commented/$",
        views.CommentedFQIDView.as_view(),
        name="author-commented-fqid",
    ),
    re_path(
        r"^api/authors/(?P<author_fqid>https?://[^/]+/.+)/liked/$",
        views.ThingsLikedByAuthorFQIDView.as_view(),
        name="things-liked-by-author-fqid",
    ),
    re_path(
        r"^api/liked/(?P<like_fqid>.+)/$",
        views.SingleLikeFQIDView.as_view(),
        name="single-like-fqid",
    ),
    re_path(
        r"^api/authors/(?P<author_serial>[^/]+)/posts/(?P<post_serial>[^/]+)/comments/(?P<comment_fqid>.+)/likes/$",
        views.CommentLikesView.as_view(),
        name="comment-likes",
    ),
    re_path(
        r"^api/posts/(?P<post_fqid>.+)/likes/$",
        views.PostLikesFQIDAPIView.as_view(),
        name="post-likes-fqid",
    ),
    # Retrieve a specific comment using its FQID (local)
    re_path(
        r"^api/commented/(?P<comment_fqid>.+)/$",
        views.SingleCommentedView.as_view(),
        name="comment-detail",
    ),
    # Comments endpoint for a specific post
    re_path(
        r"^api/posts/(?P<post_fqid>.+)/comments/$",
        views.PostCommentsViewFQID.as_view(),
        name="post-comments-fqid",
    ),
    # Retrieve a specific comment using its FQID (local)
    re_path(
        r"^api/authors/(?P<author_serial>[^/]+)/post/(?P<post_serial>[^/]+)/comment/(?P<remote_comment_fqid>.+)/$",
        views.RemoteCommentView.as_view(),
        name="remote-comment-detail",
    ),
    re_path(
        r"^api/posts/(?P<post_fqid>.+)/image/$",
        views.PostImageViewFQID.as_view(),
        name="post-detail-image",
    ),
    # retrieve specific post using its FQID
    re_path(
        r"^api/posts/(?P<post_fqid>.+)/$",
        views.SinglePostView.as_view(),
        name="post-detail",
    ),
    path(
        "api/authors/<str:author_serial>/posts/<str:post_serial>/comments/",
        views.PostCommentsView.as_view(),
        name="post-comments",
    ),
    path(
        "api/authors/<str:author_serial>/liked/",
        views.ThingsLikedByAuthorView.as_view(),
        name="author-liked",
    ),
    path(
        "api/authors/<str:author_serial>/liked/<str:like_serial>/",
        views.SingleLikeView.as_view(),
        name="single-like",
    ),
]
#
