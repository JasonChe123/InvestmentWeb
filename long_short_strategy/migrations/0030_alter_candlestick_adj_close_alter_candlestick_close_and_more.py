# Generated by Django 5.1.2 on 2024-12-05 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('long_short_strategy', '0029_delete_incomestatement'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candlestick',
            name='adj_close',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='candlestick',
            name='close',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='candlestick',
            name='high',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='candlestick',
            name='low',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='candlestick',
            name='open',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='candlestick',
            name='volume',
            field=models.IntegerField(null=True),
        ),
    ]