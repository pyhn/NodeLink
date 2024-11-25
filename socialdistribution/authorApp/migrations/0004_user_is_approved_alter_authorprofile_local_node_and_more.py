# Generated by Django 5.1.1 on 2024-11-03 12:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authorApp", "0003_remove_friends_unique_friendship_and_more"),
        ("node_link", "0002_alter_node_created_by_alter_node_deleted_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_approved",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="authorprofile",
            name="local_node",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="node_link.node"
            ),
        ),
        migrations.AlterField(
            model_name="follower",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_created",
                to="authorApp.authorprofile",
            ),
        ),
        migrations.AlterField(
            model_name="follower",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_updated",
                to="authorApp.authorprofile",
            ),
        ),
        migrations.AlterField(
            model_name="friends",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_created",
                to="authorApp.authorprofile",
            ),
        ),
        migrations.AlterField(
            model_name="friends",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_updated",
                to="authorApp.authorprofile",
            ),
        ),
    ]