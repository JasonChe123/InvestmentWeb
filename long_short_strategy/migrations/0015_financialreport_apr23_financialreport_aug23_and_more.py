# Generated by Django 5.1.2 on 2024-11-09 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('long_short_strategy', '0014_financialreport_jul23'),
    ]

    operations = [
        migrations.AddField(
            model_name='financialreport',
            name='Apr23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Aug23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Dec23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Feb23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Jan23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Jun23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Mar23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='May23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Nov23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Oct23',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='financialreport',
            name='Sep23',
            field=models.JSONField(null=True),
        ),
    ]
