# Generated by Django 5.1.1 on 2024-11-15 02:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authorApp", "0005_user_github_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="authorprofile",
            name="last_github_event_id",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
