# Generated by Django 5.1.1 on 2024-10-17 20:15

import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_link", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="github_token",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="author",
            name="github_url",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="author",
            name="github_user",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="comment",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(class)s_updated",
                to="node_link.author",
            ),
        ),
        migrations.AlterField(
            model_name="follower",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="follower",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="follower",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(class)s_updated",
                to="node_link.author",
            ),
        ),
        migrations.AlterField(
            model_name="friends",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="friends",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="friends",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(class)s_updated",
                to="node_link.author",
            ),
        ),
        migrations.AlterField(
            model_name="like",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="like",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="like",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(class)s_updated",
                to="node_link.author",
            ),
        ),
        migrations.AlterField(
            model_name="node",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deleted_nodes",
                to="node_link.admin",
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, default=datetime.datetime.now, null=True
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(class)s_updated",
                to="node_link.author",
            ),
        ),
    ]
