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

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email or "",
            "is_staff": True,
            "is_superuser": True,
        },
    )

    if created:
        user.set_password(password)
    else:
        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)

    user.save()
