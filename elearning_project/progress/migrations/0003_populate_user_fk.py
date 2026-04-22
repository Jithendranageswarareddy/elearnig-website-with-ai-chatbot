from django.db import migrations


def populate_user_fk(apps, schema_editor):
    LessonProgress = apps.get_model("progress", "LessonProgress")
    User = apps.get_model("accounts", "User")

    # If only one user exists, assign to all existing progress rows
    users = list(User.objects.all())
    if users:
        default_user = users[0]

        for progress in LessonProgress.objects.all():
            if not progress.user:
                progress.user = default_user
                progress.save(update_fields=["user"])


class Migration(migrations.Migration):

    dependencies = [
        ("progress", "0002_lessonprogress_user"),
    ]

    operations = [
        migrations.RunPython(populate_user_fk),
    ]