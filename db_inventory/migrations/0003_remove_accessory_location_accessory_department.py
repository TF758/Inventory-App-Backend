# Generated by Django 5.2.3 on 2025-06-23 03:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db_inventory', '0002_department_location_equipment_component_consumable_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accessory',
            name='location',
        ),
        migrations.AddField(
            model_name='accessory',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='accessories', to='db_inventory.department'),
        ),
    ]
