# Generated by Django 5.1.1 on 2024-11-15 20:41

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("postApp", "0002_alter_comment_author_alter_comment_created_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="like",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]