from django.db.models import Q
from django_filters import rest_framework as filters

from usersapi.models import CustomObtainToken


class DateContainsFilter(filters.CharFilter):
    def filter(self, qs, value):
        if not value:
            return qs
        lookup = f"{self.field_name}__icontains"
        return qs.filter(Q(**{lookup: value}))


class CustomTokenFilter(filters.FilterSet):
    created = DateContainsFilter(field_name="created")

    class Meta:
        model = CustomObtainToken
        fields = ["created"]
