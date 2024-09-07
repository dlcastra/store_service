import difflib

from django.http import JsonResponse
from django.urls import get_resolver
from rest_framework import status


def get_all_urls():
    url_patterns = get_resolver().url_patterns
    all_urls = []

    def extract_urls(patterns):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                extract_urls(pattern.url_patterns)
            else:
                try:
                    all_urls.append(pattern.pattern._route)
                except AttributeError:
                    pass

    extract_urls(url_patterns)
    return all_urls


def find_closest_match(requested_url, all_urls):
    closest_matches = difflib.get_close_matches(requested_url, all_urls, n=1, cutoff=0.3)
    return closest_matches[0] if closest_matches else None


def custom_404(request, exception=None):
    requested_url = request.path
    all_urls = get_all_urls()
    closest_match = find_closest_match(requested_url, all_urls)

    if closest_match:
        message = f"Page not found. Maybe you meant: '{closest_match}'?"
    else:
        message = "Page not found. Check the URL and try again."

    return JsonResponse({"error": message}, status=status.HTTP_404_NOT_FOUND)


def custom_500(request, exception=None):
    return JsonResponse(
        {"error": "Something went wrong, server unavailable"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
