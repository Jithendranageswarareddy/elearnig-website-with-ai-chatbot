import os
from collections import OrderedDict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.db import transaction

from accounts.models import SystemLog, User
from chatbot.models import (
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
from contact.models import ContactMessage
from courses.models import Bookmark, History, Lesson, Semester, Subject, Unit
from progress.models import LessonProgress


ANALYSIS_MODELS = OrderedDict(
    [
        ("Users (KEEP)", User),
        ("ReferencePDF", ReferencePDF),
        ("PDFPageChunk", PDFPageChunk),
        ("ChunkEmbedding", ChunkEmbedding),
        ("ChatQuery", ChatQuery),
        ("ChatQA", ChatQA),
        ("Subject", Subject),
        ("Unit", Unit),
        ("Lesson", Lesson),
        ("Semester", Semester),
        ("Bookmark", Bookmark),
        ("History", History),
        ("LessonProgress", LessonProgress),
        ("SystemLog", SystemLog),
        ("ContactMessage", ContactMessage),
        ("GeneratedQuestion", GeneratedQuestion),
        ("ChunkConceptLink", ChunkConceptLink),
        ("ConceptNode", ConceptNode),
        ("ConceptRelation", ConceptRelation),
        ("ConceptRelationship", ConceptRelationship),
        ("ConceptAnswerCache", ConceptAnswerCache),
        ("RetrievalStrategyCache", RetrievalStrategyCache),
        ("AdminLogEntry", LogEntry),
        ("Session", Session),
    ]
)

DELETE_ORDER = [
    # Requested FK order core
    ChunkEmbedding,
    PDFPageChunk,
    ReferencePDF,
    ChatQuery,
    Lesson,
    Unit,
    Subject,
    Semester,
    # Related data/log/test-data cleanup
    GeneratedQuestion,
    ChunkConceptLink,
    ConceptRelation,
    ConceptRelationship,
    ConceptAnswerCache,
    RetrievalStrategyCache,
    ConceptNode,
    ChatQA,
    LessonProgress,
    History,
    Bookmark,
    SystemLog,
    ContactMessage,
    LogEntry,
    Session,
]


def print_counts(header):
    print(f"\n{header}")
    print("-" * len(header))
    for name, model in ANALYSIS_MODELS.items():
        print(f"{name:24}: {model.objects.count()}")


def main():
    print("STEP 1: MODEL ANALYSIS")
    print("----------------------")
    print("Identified cleanup targets for PDFs/chunks/embeddings/chat/subjects/units/lessons/progress/logs.")
    print("User model (accounts_user) will be preserved.")

    print_counts("BEFORE CLEANUP COUNTS")

    print("\nSTEP 2 & 3: DELETE DATA (NOT TABLES) IN FK-SAFE ORDER")
    print("------------------------------------------------------")

    with transaction.atomic():
        for model in DELETE_ORDER:
            deleted, _ = model.objects.all().delete()
            print(f"Deleted {deleted:6} rows from {model.__name__}")

    print_counts("AFTER CLEANUP COUNTS")

    print("\nSTEP 4: REQUIRED VERIFICATION COUNTS")
    print("------------------------------------")
    print(f"Users      : {User.objects.count()}")
    print(f"Subjects   : {Subject.objects.count()}")
    print(f"Units      : {Unit.objects.count()}")
    print(f"PDFs       : {ReferencePDF.objects.count()}")
    print(f"Chunks     : {PDFPageChunk.objects.count()}")
    print(f"Embeddings : {ChunkEmbedding.objects.count()}")

    users_ok = User.objects.count() >= 1
    others_empty = all(
        model.objects.count() == 0
        for model in [
            Subject,
            Unit,
            Lesson,
            Semester,
            ReferencePDF,
            PDFPageChunk,
            ChunkEmbedding,
            ChatQuery,
            LessonProgress,
            SystemLog,
            ContactMessage,
            Bookmark,
            History,
            ChatQA,
            GeneratedQuestion,
            ChunkConceptLink,
            ConceptNode,
            ConceptRelation,
            ConceptRelationship,
            ConceptAnswerCache,
            RetrievalStrategyCache,
            LogEntry,
            Session,
        ]
    )

    print("\nSTEP 5: INTEGRITY SNAPSHOT")
    print("--------------------------")
    print(f"Users remain   : {'YES' if users_ok else 'NO'}")
    print(f"Other tables   : {'EMPTY' if others_empty else 'NOT EMPTY'}")

    if not users_ok:
        raise RuntimeError("User table became empty unexpectedly.")
    if not others_empty:
        raise RuntimeError("One or more non-user tables still contain data.")

    print("\nDatabase cleaned successfully. Ready for structured academic data insertion.")


if __name__ == "__main__":
    main()
