# Generated by Django 5.1.1 on 2025-02-23 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Medi', '0003_prescription_prescriptionitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='doctor_profiles/'),
        ),
    ]
