from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TeacherProfile

@receiver(post_save, sender=User)
def ensure_teacher_profile(sender, instance, created, **kwargs):
    if created:
        TeacherProfile.objects.create(
            user=instance,
            avatar_text=(instance.first_name or instance.username)[:1],
        )
