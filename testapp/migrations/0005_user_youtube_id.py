# Generated by Django 3.1.7 on 2021-03-29 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0004_auto_20210322_1541'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='youtube_id',
            field=models.CharField(default='', max_length=30, verbose_name='YouTubeChannelID'),
        ),
    ]
