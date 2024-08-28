# Generated by Django 5.1 on 2024-08-28 13:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usersapi", "0002_rename_invitation_code_customuser_referral_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="user_own_invite_code",
            field=models.CharField(max_length=15, unique=True),
        ),
        migrations.CreateModel(
            name="Wallet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "address",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("wallet_balance", models.IntegerField(default=0)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
