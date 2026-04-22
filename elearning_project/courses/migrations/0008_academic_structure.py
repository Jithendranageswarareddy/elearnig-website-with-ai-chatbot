from django.db import migrations, models


def create_semesters(apps, schema_editor):
    Semester = apps.get_model('courses', 'Semester')
    for i in range(1, 9):
        Semester.objects.create(number=i, regulation=f"Regulation {i}")


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_remove_bookmark_legacy_user_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveSmallIntegerField()),
                ('regulation', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField(
            model_name='subject',
            name='semester',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, to='courses.semester'),
        ),
        migrations.AddField(
            model_name='subject',
            name='subject_code',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='subject',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(create_semesters),
    ]
