# Generated by Django 5.1 on 2024-11-20 17:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallet", "0004_paymenttransaction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymenttransaction",
            name="currency",
            field=models.IntegerField(default=840),
        ),
    ]
