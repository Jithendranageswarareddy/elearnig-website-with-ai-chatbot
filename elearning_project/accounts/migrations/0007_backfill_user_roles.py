from django.db import migrations


def backfill_user_roles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all():
        if user.is_superuser:
            user.role = "PRINCIPAL"
            user.is_staff = True
        elif user.is_staff:
            user.role = "FACULTY"
        else:
            user.role = "STUDENT"
            user.is_staff = False
        user.save(update_fields=["role", "is_staff"])


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_user_role"),
    ]

    operations = [
        migrations.RunPython(backfill_user_roles, noop_reverse),
    ]
