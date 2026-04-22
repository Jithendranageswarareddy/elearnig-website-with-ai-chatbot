from django.db import migrations
from django.contrib.auth.hashers import make_password


def migrate_learner_to_user(apps, schema_editor):
    Learner = apps.get_model('accounts', 'Learner')
    User = apps.get_model('accounts', 'User')

    for learner in Learner.objects.all():
        if User.objects.filter(email=learner.email).exists():
            continue

        User.objects.create(
            id=learner.id,  # Preserve primary key
            email=learner.email,
            name=learner.name,
            password=make_password(learner.password),
            is_active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user'),  # Adjust if needed
    ]

    operations = [
        migrations.RunPython(migrate_learner_to_user),
    ]