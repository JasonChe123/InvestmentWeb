# Generated by Django 5.1.2 on 2024-11-14 10:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('long_short_strategy', '0027_alter_financialreport_basiceps_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='balancesheet',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock'),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock'),
        ),
        migrations.AlterField(
            model_name='financialreport',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock'),
        ),
        migrations.AlterField(
            model_name='incomestatement',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock'),
        ),
    ]
