# Generated by Django 5.1.2 on 2024-11-09 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('long_short_strategy', '0016_financialreport_apr24_financialreport_aug24_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stock',
            name='ipo_year',
            field=models.IntegerField(null=True),
        ),
    ]
