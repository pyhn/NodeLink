# Generated by Django 5.1.1 on 2024-11-17 22:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("authorApp", "0006_authorprofile_last_github_event_id"),
        ("node_link", "0003_node_is_active_node_password_node_username_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={},
        ),
        migrations.RemoveField(
            model_name="authorprofile",
            name="local_node",
        ),
        migrations.AddField(
            model_name="user",
            name="local_node",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="node_link.node",
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=("local_node", "username"), name="unique_user_node_combination"
            ),
        ),
    ]