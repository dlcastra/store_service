from celery import shared_task
from django.core.mail import send_mail
from decouple import config


@shared_task
def send_registration_email(email, context):
    send_mail(
        subject="Registration complete",
        message=f"Hi {context['username']}, welcome to NFT shop. Login to receive your authorization token",
        from_email="governmentguardian0@gmail.com",  # config("EMAIL_HOST_APP"),
        recipient_list=[email],
        fail_silently=False,
    )
