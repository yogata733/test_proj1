from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    user_id = models.CharField('ユーザーID', unique=True, max_length=20)
    email = models.EmailField('メールアドレス', unique=True)
    youtube_id = models.CharField(
        'YouTubeChannelID', max_length=30, default='')
