# Generated by Django 5.1.1 on 2024-11-17 23:33

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authorApp", "0008_alter_user_local_node"),
        ("node_link", "0003_node_is_active_node_password_node_username_and_more"),
        ("postApp", "0003_like_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddConstraint(
            model_name="post",
            constraint=models.UniqueConstraint(
                fields=("uuid", "node"), name="unique_uuid_node_combination"
            ),
        ),
    ]