# Generated by Django 5.1.2 on 2025-03-18 23:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manage_database', '0011_remove_candlestick_adj_close_alter_candlestick_close_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candlestick',
            name='volume',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='candlestick',
            unique_together={('stock', 'date')},
        ),
    ]
