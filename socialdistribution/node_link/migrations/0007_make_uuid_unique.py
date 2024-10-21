# Generated by Django 5.1.1 on 2024-10-19 00:10

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("node_link", "0006_add_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
