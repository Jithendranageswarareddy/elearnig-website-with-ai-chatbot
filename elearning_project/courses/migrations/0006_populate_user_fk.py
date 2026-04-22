from django.db import migrations


def populate_user_fk(apps, schema_editor):
    Bookmark = apps.get_model("courses", "Bookmark")
    History = apps.get_model("courses", "History")
    User = apps.get_model("accounts", "User")

    # Populate Bookmark.user
    for bookmark in Bookmark.objects.all():
        if bookmark.legacy_user_id:
            try:
                user = User.objects.get(id=bookmark.legacy_user_id)
                bookmark.user = user
                bookmark.save(update_fields=["user"])
            except User.DoesNotExist:
                pass

    # Populate History.user
    for history in History.objects.all():
        if history.legacy_user_id:
            try:
                user = User.objects.get(id=history.legacy_user_id)
                history.user = user
                history.save(update_fields=["user"])
            except User.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0005_rename_user_id_bookmark_legacy_user_id_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_user_fk),
    ]