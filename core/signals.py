import os

from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_admin_user(sender, **kwargs):
    if sender.name != "core":
        return

    username = os.getenv("ADMIN_USERNAME")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        return

    User = get_user_model()

    if User.objects.filter(username=username).exists():
        return

    User.objects.create_superuser(
        username=username,
        email=email or "",
        password=password,
    )
