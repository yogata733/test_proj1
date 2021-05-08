from django.db import models
from django.contrib.auth.models import AbstractUser


class YoutubeChannel(models.Model):
    channelid = models.CharField(
        'チャンネルID',
        max_length=100, blank=False, null=False, unique=True)
    title = models.CharField(
        'チャンネルタイトル',
        max_length=100, blank=False, null=False)
    description = models.TextField(
        '説明',
        blank=True, null=False)
    subscriberCount = models.IntegerField(
        '登録者数',
        blank=False, null=False)

    def __str__(self):
        return self.title


class User(AbstractUser):
    user_id = models.CharField(
        'ユーザーID',
        unique=True, max_length=20)
    email = models.EmailField(
        'メールアドレス',
        unique=True)
    yt_channels = models.ManyToManyField(
        YoutubeChannel,
        blank=True, related_name='yt_channels')
    yt_subscriptions = models.ManyToManyField(
        YoutubeChannel,
        blank=True, related_name='yt_subscriptions')
