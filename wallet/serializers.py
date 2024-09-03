from datetime import datetime

from rest_framework import serializers

from wallet.models import WalletToWalletTransaction
from wallet.utils import decrypt_data


class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletToWalletTransaction
        fields = ["transaction_id", "wallet_addr_to", "user_to", "amount", "currency", "timestamp"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        timestamp = str(instance.timestamp)
        date_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f%z")
        formatted_date = date_obj.strftime("%Y-%m-%d | %H:%M:%S")

        ret["wallet_addr_to"] = decrypt_data(ret["wallet_addr_to"])
        ret["user_to"] = instance.user_to.username
        ret["timestamp"] = formatted_date

        return ret
