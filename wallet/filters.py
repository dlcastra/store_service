from django_filters import rest_framework as rest_filters

from usersapi.filters import DateContainsFilter
from wallet.models import WalletToWalletTransaction


class TransactionsFilter(rest_filters.FilterSet):
    timestamp = DateContainsFilter(field_name="timestamp")

    class Meta:
        model = WalletToWalletTransaction
        fields = ["timestamp"]
