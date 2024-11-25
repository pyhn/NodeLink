# Generated by Django 5.1.1 on 2024-11-25 02:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authorApp", "0010_alter_authorprofile_fqid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authorprofile",
            name="last_github_event_id",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="display_name",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="user",
            name="profileImage",
            field=models.URLField(
                default="https://s3.amazonaws.com/37assets/svn/765-default-avatar.png",
                max_length=255,
            ),
        ),
    ]