from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def rename_uploadedpdf(apps, schema_editor):
    # nothing to do here; RenameModel will handle
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0006_pdfpagechunk'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UploadedPDF',
            new_name='ReferencePDF',
        ),
        migrations.RenameField(
            model_name='referencepdf',
            old_name='user',
            new_name='uploaded_by',
        ),
        migrations.AddField(
            model_name='referencepdf',
            name='subject',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.subject', null=True, blank=True),
        ),
        migrations.RenameField(
            model_name='pdfpagechunk',
            old_name='pdf',
            new_name='reference_pdf',
        ),
        migrations.AddField(
            model_name='referencepdf',
            name='is_syllabus_reference',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='referencepdf',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='referencepdf',
            name='uploaded_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.RemoveField(
            model_name='pdfpagechunk',
            name='subject',
        ),
        migrations.RemoveField(
            model_name='pdfpagechunk',
            name='image_paths',
        ),
        migrations.AddField(
            model_name='pdfpagechunk',
            name='metadata',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterModelOptions(
            name='pdfpagechunk',
            options={'ordering': ['reference_pdf', 'page_number']},
        ),
        migrations.AddIndex(
            model_name='pdfpagechunk',
            index=models.Index(fields=['text_content'], name='text_content_idx'),
        ),
    ]
