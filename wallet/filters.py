from django_filters import rest_framework as rest_filters

# from usersapi.filters import DateContainsFilter
from wallet.models import WalletToWalletTransaction


class DateContainsFilter(rest_filters.CharFilter):
    def filter(self, qs, value):
        if not value:
            return qs
        return qs.filter(timestamp__contains=value)


class TransactionsFilter(rest_filters.FilterSet):
    # created_at = DateContainsFilter(field_name="timestamp")

    class Meta:
        model = WalletToWalletTransaction
        fields = ["timestamp"]
