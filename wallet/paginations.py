from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import defaultdict
from .serializers import TransactionHistorySerializer

from datetime import datetime


class TransactionPagination(PageNumberPagination):
    page_size = 20

    def paginate_queryset(self, queryset, request, view=None):
        self.page = super().paginate_queryset(queryset, request, view)
        return self.page

    def group_transactions_by_year_and_month(self, transactions):
        # Группируем транзакции по годам и месяцам
        grouped_data = defaultdict(lambda: defaultdict(list))
        for transaction in transactions:
            # Конвертируем строку времени обратно в объект datetime
            timestamp = datetime.strptime(transaction["timestamp"], "%Y-%m-%d | %H:%M:%S")
            year = timestamp.year
            month = timestamp.month
            grouped_data[year][month].append(transaction)
        return grouped_data

    def get_paginated_response(self, data):
        serialized_data = TransactionHistorySerializer(self.page, many=True).data
        grouped_data = self.group_transactions_by_year_and_month(serialized_data)

        result = {}
        for year, months in grouped_data.items():
            result[year] = {"months": {}}
            for month, transactions in months.items():
                result[year]["months"][month] = {"data": transactions}
        return Response({"results": result})
