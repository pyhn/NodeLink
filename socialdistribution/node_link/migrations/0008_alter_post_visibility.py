# Generated by Django 5.1.1 on 2024-10-19 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_link", "0007_make_uuid_unique"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("p", "public"),
                    ("u", "unlisted"),
                    ("fo", "friends-only"),
                    ("d", "deleted"),
                ],
                default="p",
                max_length=2,
            ),
        ),
    ]
