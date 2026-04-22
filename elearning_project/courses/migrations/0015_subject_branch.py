from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_unit_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='branch',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
