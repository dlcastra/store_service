# Generated by Django 5.1 on 2024-08-30 16:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallet", "0002_alter_wallet_wallet_balance_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wallettowallettransaction",
            name="wallet_addr_from",
            field=models.CharField(max_length=185),
        ),
        migrations.AlterField(
            model_name="wallettowallettransaction",
            name="wallet_addr_to",
            field=models.CharField(max_length=185),
        ),
    ]