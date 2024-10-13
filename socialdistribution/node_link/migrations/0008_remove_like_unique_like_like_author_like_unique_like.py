# Generated by Django 5.1.1 on 2024-10-13 22:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('node_link', '0007_alter_comment_content'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='like',
            name='unique_like',
        ),
        migrations.AddField(
            model_name='like',
            name='author',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='node_link.author'),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='like',
            constraint=models.UniqueConstraint(fields=('author', 'post'), name='unique_like'),
        ),
    ]
