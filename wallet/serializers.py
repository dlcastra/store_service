from rest_framework import serializers

from wallet.models import WalletToWalletTransaction
from wallet.utils import decrypt_data


class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletToWalletTransaction
        fields = ["transaction_id", "wallet_addr_to", "user_to", "amount", "currency", "timestamp"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["wallet_addr_to"] = decrypt_data(ret["wallet_addr_to"])

        return ret
