from django.db import models
from datetime import datetime


class MixinApp(models.Model):
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        "authorApp.AuthorProfile",
        on_delete=models.PROTECT,
        related_name="%(class)s_created",
    )

    updated_at = models.DateTimeField(default=datetime.now, null=True, blank=True)

    updated_by = models.ForeignKey(
        "authorApp.AuthorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(class)s_updated",
    )

    deleted_at = models.DateTimeField(default=datetime.now, null=True, blank=True)

    class Meta:
        abstract = True
