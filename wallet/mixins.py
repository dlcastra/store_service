from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from usersapi.models import CustomUser
from wallet.models import Wallet, WalletToWalletTransaction
from wallet.utils import encrypt_data


class WalletTransactionMixin:
    def _error_response(self, message):
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    def _get_wallet_from_user(self, user):
        try:
            return Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return None

    def _get_wallet_to_and_user_to(self, wallet_addr_to):
        try:
            wallet_to = Wallet.objects.get(address=wallet_addr_to)
            user_to = CustomUser.objects.get(id=wallet_to.user_id)
            return wallet_to, user_to

        except (Wallet.DoesNotExist, IntegrityError):
            return None, None

    def _validate_amount(self, amount):
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return None
            return amount

        except (ValueError, TypeError, InvalidOperation):
            return None

    def _perform_transaction(self, user_from, user_to, wallet_from, wallet_to, amount):
        try:
            with transaction.atomic():
                wallet_from.wallet_balance -= amount
                wallet_to.wallet_balance += amount
                wallet_from.save()
                wallet_to.save()

                transaction_record = WalletToWalletTransaction.objects.create(
                    user_from=user_from,
                    user_to=user_to,
                    wallet_addr_from=encrypt_data(wallet_from.address),
                    wallet_addr_to=encrypt_data(wallet_to.address),
                    amount=amount,
                )
                return transaction_record.transaction_id
        except Exception as e:
            transaction.rollback()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _check_transaction_duplicate(self, user_from, user_to, wallet_from, wallet_to, amount):
        recent_transaction = (
            WalletToWalletTransaction.objects.filter(
                user_from=user_from,
                user_to=user_to,
                wallet_addr_from=encrypt_data(wallet_from.address),
                wallet_addr_to=encrypt_data(wallet_to.address),
                amount=amount,
            )
            .order_by("-timestamp")
            .first()
        )
        if recent_transaction and (timezone.now() - recent_transaction.timestamp).total_seconds() < 60:
            self._error_response("Duplicate transaction detected. Please wait before retrying.")
