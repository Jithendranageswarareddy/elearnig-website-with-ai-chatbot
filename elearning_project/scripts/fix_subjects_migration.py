import os
import sys
import traceback

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')

try:
    import django
    django.setup()
    from django.db import transaction
    from django.core.management import call_command
    from courses.models import Semester, Subject
    from chatbot.models import ReferencePDF

    with transaction.atomic():
        subj = Subject.objects.first()
        created = False
        if subj is None:
            sem = Semester.objects.first()
            if sem is None:
                sem = Semester.objects.create(name='General Semester', number=0, is_active=True)
                print('Created default Semester id', sem.id)
            subj = Subject.objects.create(name='General', subject_code='GEN101', semester=sem, is_active=True)
            created = True
            print('Created default Subject id', subj.id)
        else:
            print('Existing Subject id found', subj.id)

        # Backfill ReferencePDF with NULL subject
        null_qs = ReferencePDF.objects.filter(subject__isnull=True)
        null_count = null_qs.count()
        if null_count:
            null_qs.update(subject=subj)
            print('Backfilled ReferencePDF.subject for', null_count, 'rows to subject id', subj.id)
        else:
            print('No ReferencePDF rows with NULL subject found')

    # run makemigrations and migrate
    try:
        print('Running makemigrations --noinput')
        call_command('makemigrations', '--noinput')
    except Exception as e:
        print("ERROR:", str(e))
        print('makemigrations produced an error:')
        traceback.print_exc()

    try:
        print('Running migrate --noinput')
        call_command('migrate', '--noinput')
        print('MIGRATE_SUCCESS')
    except Exception as e:
        print("ERROR:", str(e))
        print('migrate failed:')
        traceback.print_exc()

    # final verification
    total_referencepdf = ReferencePDF.objects.count()
    null_after = ReferencePDF.objects.filter(subject__isnull=True).count()
    print('Final Subject id used:', subj.id)
    print('Total ReferencePDF rows:', total_referencepdf)
    print('ReferencePDF rows still NULL subject:', null_after)
    status = 'SUCCESS' if null_after == 0 else 'FAILURE'
    print('Migration status:', status)

except Exception as e:
    print("ERROR:", str(e))
    print('ERROR during script:')
    traceback.print_exc()
    sys.exit(1)
