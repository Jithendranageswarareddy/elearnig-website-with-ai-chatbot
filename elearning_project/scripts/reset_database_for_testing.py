import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django  # noqa: E402

django.setup()

from django.db import connection, transaction  # noqa: E402
from django.core.management.color import no_style  # noqa: E402

from accounts.models import SystemLog, User  # noqa: E402
from chatbot.models import (  # noqa: E402
    ChatQA,
    ChatQuery,
    ChunkConceptLink,
    ChunkEmbedding,
    ConceptAnswerCache,
    ConceptNode,
    ConceptRelation,
    ConceptRelationship,
    GeneratedQuestion,
    PDFPageChunk,
    ReferencePDF,
    RetrievalStrategyCache,
)
from contact.models import ContactMessage  # noqa: E402
from courses.models import Bookmark, History, Lesson, Semester, Subject, Unit  # noqa: E402
from progress.models import LessonProgress  # noqa: E402


KEEP_SUPERUSER = os.getenv("KEEP_SUPERUSER", "0").strip() in {"1", "true", "yes", "on"}


TABLE_MODELS = [
    SystemLog,
    ContactMessage,
    ChatQuery,
    ChatQA,
    ChunkConceptLink,
    ConceptRelation,
    ConceptRelationship,
    ConceptNode,
    ConceptAnswerCache,
    RetrievalStrategyCache,
    GeneratedQuestion,
    ChunkEmbedding,
    PDFPageChunk,
    ReferencePDF,
    Bookmark,
    History,
    LessonProgress,
    Lesson,
    Unit,
    Subject,
    Semester,
]


def _clear_project_tables():
    for model in TABLE_MODELS:
        model.objects.all().delete()

    if KEEP_SUPERUSER:
        User.objects.filter(is_superuser=False).delete()
    else:
        User.objects.all().delete()


def _reset_sequences():
    sequence_models = TABLE_MODELS + [User]
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            table_names = [model._meta.db_table for model in sequence_models]
            quoted_names = ",".join(f"'{table_name}'" for table_name in table_names)
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({quoted_names})")
        else:
            for sql in connection.ops.sequence_reset_sql(no_style(), sequence_models):
                cursor.execute(sql)


def _print_counts():
    print("accounts_user", User.objects.count())
    print("courses_semester", Semester.objects.count())
    print("courses_subject", Subject.objects.count())
    print("courses_unit", Unit.objects.count())
    print("courses_lesson", Lesson.objects.count())
    print("chatbot_referencepdf", ReferencePDF.objects.count())
    print("chatbot_pdfpagechunk", PDFPageChunk.objects.count())
    print("chatbot_chatquery", ChatQuery.objects.count())
    print("accounts_systemlog", SystemLog.objects.count())
    print("contact_contactmessage", ContactMessage.objects.count())


def main():
    with transaction.atomic():
        _clear_project_tables()
        _reset_sequences()
    _print_counts()


if __name__ == "__main__":
    main()
