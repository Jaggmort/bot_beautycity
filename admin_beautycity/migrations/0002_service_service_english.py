# Generated by Django 4.2 on 2023-05-24 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_beautycity', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='service_english',
            field=models.CharField(default=None, max_length=30, verbose_name='По_английски_через "_"'),
        ),
    ]