# Generated by Django 5.1.1 on 2024-11-20 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("postApp", "0005_remove_post_unique_uuid_node_combination_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="contentType",
            field=models.CharField(
                choices=[
                    ("a", "application/base64"),
                    ("png", "image/png;base64"),
                    ("jpeg", "image/jpeg;base64"),
                    ("p", "text/plain"),
                    ("m", "text/markdown"),
                ],
                default="p",
                max_length=10,
            ),
        ),
    ]
