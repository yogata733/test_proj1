# Generated by Django 3.1.7 on 2021-03-22 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0003_auto_20210322_1256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_id',
            field=models.CharField(max_length=20, unique=True, verbose_name='ユーザーID'),
        ),
    ]