# Generated by Django 5.1.2 on 2024-11-09 22:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('long_short_strategy', '0018_alter_stock_market_cap'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceSheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Jan23', models.JSONField(null=True)),
                ('Feb23', models.JSONField(null=True)),
                ('Mar23', models.JSONField(null=True)),
                ('Apr23', models.JSONField(null=True)),
                ('May23', models.JSONField(null=True)),
                ('Jun23', models.JSONField(null=True)),
                ('Jul23', models.JSONField(null=True)),
                ('Aug23', models.JSONField(null=True)),
                ('Sep23', models.JSONField(null=True)),
                ('Oct23', models.JSONField(null=True)),
                ('Nov23', models.JSONField(null=True)),
                ('Dec23', models.JSONField(null=True)),
                ('Jan24', models.JSONField(null=True)),
                ('Feb24', models.JSONField(null=True)),
                ('Mar24', models.JSONField(null=True)),
                ('Apr24', models.JSONField(null=True)),
                ('May24', models.JSONField(null=True)),
                ('Jun24', models.JSONField(null=True)),
                ('Jul24', models.JSONField(null=True)),
                ('Aug24', models.JSONField(null=True)),
                ('Sep24', models.JSONField(null=True)),
                ('Oct24', models.JSONField(null=True)),
                ('Nov24', models.JSONField(null=True)),
                ('Dec24', models.JSONField(null=True)),
                ('symbol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock')),
            ],
        ),
        migrations.CreateModel(
            name='CashFlow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Jan23', models.JSONField(null=True)),
                ('Feb23', models.JSONField(null=True)),
                ('Mar23', models.JSONField(null=True)),
                ('Apr23', models.JSONField(null=True)),
                ('May23', models.JSONField(null=True)),
                ('Jun23', models.JSONField(null=True)),
                ('Jul23', models.JSONField(null=True)),
                ('Aug23', models.JSONField(null=True)),
                ('Sep23', models.JSONField(null=True)),
                ('Oct23', models.JSONField(null=True)),
                ('Nov23', models.JSONField(null=True)),
                ('Dec23', models.JSONField(null=True)),
                ('Jan24', models.JSONField(null=True)),
                ('Feb24', models.JSONField(null=True)),
                ('Mar24', models.JSONField(null=True)),
                ('Apr24', models.JSONField(null=True)),
                ('May24', models.JSONField(null=True)),
                ('Jun24', models.JSONField(null=True)),
                ('Jul24', models.JSONField(null=True)),
                ('Aug24', models.JSONField(null=True)),
                ('Sep24', models.JSONField(null=True)),
                ('Oct24', models.JSONField(null=True)),
                ('Nov24', models.JSONField(null=True)),
                ('Dec24', models.JSONField(null=True)),
                ('symbol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock')),
            ],
        ),
        migrations.CreateModel(
            name='IncomeStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Jan23', models.JSONField(null=True)),
                ('Feb23', models.JSONField(null=True)),
                ('Mar23', models.JSONField(null=True)),
                ('Apr23', models.JSONField(null=True)),
                ('May23', models.JSONField(null=True)),
                ('Jun23', models.JSONField(null=True)),
                ('Jul23', models.JSONField(null=True)),
                ('Aug23', models.JSONField(null=True)),
                ('Sep23', models.JSONField(null=True)),
                ('Oct23', models.JSONField(null=True)),
                ('Nov23', models.JSONField(null=True)),
                ('Dec23', models.JSONField(null=True)),
                ('Jan24', models.JSONField(null=True)),
                ('Feb24', models.JSONField(null=True)),
                ('Mar24', models.JSONField(null=True)),
                ('Apr24', models.JSONField(null=True)),
                ('May24', models.JSONField(null=True)),
                ('Jun24', models.JSONField(null=True)),
                ('Jul24', models.JSONField(null=True)),
                ('Aug24', models.JSONField(null=True)),
                ('Sep24', models.JSONField(null=True)),
                ('Oct24', models.JSONField(null=True)),
                ('Nov24', models.JSONField(null=True)),
                ('Dec24', models.JSONField(null=True)),
                ('symbol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='long_short_strategy.stock')),
            ],
        ),
    ]
