# Generated by Django 5.1.1 on 2024-11-19 23:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authorApp", "0008_alter_user_local_node"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={"verbose_name": "user", "verbose_name_plural": "users"},
        ),
        migrations.RemoveConstraint(
            model_name="user",
            name="unique_user_node_combination",
        ),
        migrations.AddField(
            model_name="authorprofile",
            name="fqid",
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="user",
            name="user_serial",
            field=models.CharField(default="", max_length=150),
        ),
    ]