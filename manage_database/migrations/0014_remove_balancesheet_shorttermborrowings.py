# Generated by Django 5.1.2 on 2025-03-26 13:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manage_database', '0013_remove_balancesheet_cashandcashequivalents'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='balancesheet',
            name='ShortTermBorrowings',
        ),
    ]
