# Generated by Django 5.2.3 on 2025-06-28 12:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db_inventory', '0008_remove_component_identifier'),
    ]

    operations = [
        migrations.AddField(
            model_name='component',
            name='identifier',
            field=models.CharField(blank=True, editable=False, max_length=255, unique=True),
        ),
    ]
