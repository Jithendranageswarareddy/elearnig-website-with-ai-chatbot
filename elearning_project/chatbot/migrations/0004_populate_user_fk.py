from django.db import migrations


def populate_user_fk(apps, schema_editor):
    UploadedPDF = apps.get_model("chatbot", "UploadedPDF")
    User = apps.get_model("accounts", "User")

    users = list(User.objects.all())
    if users:
        default_user = users[0]

        for pdf in UploadedPDF.objects.all():
            if not pdf.user:
                pdf.user = default_user
                pdf.save(update_fields=["user"])


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0003_uploadedpdf_user"),
    ]

    operations = [
        migrations.RunPython(populate_user_fk),
    ]