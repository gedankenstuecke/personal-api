# Generated by Django 2.1.2 on 2018-10-17 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='data',
            name='data',
            field=models.TextField(default='{}'),
        ),
    ]
