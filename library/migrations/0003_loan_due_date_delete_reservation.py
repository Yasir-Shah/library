# Generated by Django 4.2 on 2025-03-05 14:41

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0002_reservation'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='due_date',
            field=models.DateField(default=datetime.date(2025, 3, 19)),
        ),
        migrations.DeleteModel(
            name='Reservation',
        ),
    ]
