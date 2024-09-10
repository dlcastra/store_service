from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from decouple import config


@shared_task
def send_email(email, subject, template_name, context):
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=config("DEFAULT_FROM_EMAIL"),
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False,
    )
