# Generated by Django 4.2.9 on 2024-07-23 12:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('form_generator', '0002_rename_username_userdata_mail_id_userdata_user_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userdata',
            name='role',
        ),
    ]
