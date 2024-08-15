from rest_framework.pagination import PageNumberPagination


class OnlyFiveElementsPagination(PageNumberPagination):
    page_size = 5
