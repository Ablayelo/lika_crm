# Generated by Django 3.2.2 on 2021-09-01 13:17

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0082_v2_2__cremepropertytype_enabled'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='language',
            name='code',
        ),
    ]
