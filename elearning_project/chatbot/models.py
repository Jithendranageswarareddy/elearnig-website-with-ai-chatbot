from django.db import models
from django.conf import settings


class ReferencePDF(models.Model):
    class Status(models.TextChoices):
        APPROVED = "approved", "Approved"
        HOLD = "hold", "On Hold"
        REJECTED = "rejected", "Rejected"
        PROCESSING = "processing", "Processing"

    class ProcessingStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    subject = models.ForeignKey(
        "courses.Subject", on_delete=models.CASCADE, related_name="reference_pdfs"
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_pdfs",
    )
    unit = models.ForeignKey(
        "courses.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unit_pdfs",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_pdfs"
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='pdfs/')
    extracted_text = models.TextField(blank=True)
    is_syllabus_reference = models.BooleanField(default=False, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPROVED,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    processing_error = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    diagram_count = models.PositiveIntegerField(default=0)
    last_processed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "subject"],
                name="unique_reference_pdf_title_per_subject",
            )
        ]
        indexes = [
            models.Index(
                fields=["subject", "is_active", "status", "is_syllabus_reference"],
                name="chatbot_pdf_access_idx",
            ),
            models.Index(fields=["uploaded_by", "processing_status"], name="chatbot_pdf_owner_proc_idx"),
            models.Index(fields=["uploaded_by", "status"], name="chatbot_pdf_owner_status_idx"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        lesson_unit_id = getattr(getattr(self, "lesson", None), "unit_id", None)
        if lesson_unit_id:
            self.unit_id = lesson_unit_id
        super().save(*args, **kwargs)

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED

    @property
    def is_on_hold(self):
        return self.status == self.Status.HOLD

    @property
    def is_processing(self):
        return self.status == self.Status.PROCESSING


class ChatQuery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_queries",
    )
    subject = models.ForeignKey(
        "courses.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_queries",
    )
    reference_pdf = models.ForeignKey(
        ReferencePDF,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_queries",
    )
    question = models.CharField(max_length=500)
    normalized_question = models.CharField(max_length=500, blank=True)
    strict_mode = models.BooleanField(default=True)
    result_count = models.PositiveIntegerField(default=0)
    result_reference_ids = models.JSONField(default=list, blank=True)
    related_concepts = models.JSONField(default=list, blank=True)
    response_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at", "result_count"]),
        ]

    def __str__(self):
        return self.question



class ChatQA(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()

    def __str__(self):
        return self.question


class PDFPageChunk(models.Model):
    reference_pdf = models.ForeignKey(
        ReferencePDF,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    page_number = models.IntegerField()
    chunk_index = models.PositiveIntegerField(default=0)
    text_content = models.TextField()
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ["reference_pdf", "page_number", "chunk_index"]
        unique_together = ("reference_pdf", "page_number", "chunk_index")
        indexes = [
            models.Index(fields=["text_content"]),
            models.Index(fields=["reference_pdf"]),
            models.Index(fields=["page_number"]),
        ]

    def __str__(self):
        return f"PDF {self.reference_pdf_id} - page {self.page_number} - chunk {self.chunk_index}"


class ConceptNode(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)
    related_concepts = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class ChunkConceptLink(models.Model):
    chunk = models.ForeignKey(
        PDFPageChunk,
        on_delete=models.CASCADE,
        related_name="concept_links",
    )
    concept = models.ForeignKey(
        ConceptNode,
        on_delete=models.CASCADE,
        related_name="chunk_links",
    )
    relevance_score = models.FloatField(default=0.0)
    extraction_method = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_id", "-relevance_score", "concept__name"]
        unique_together = ("chunk", "concept")
        indexes = [
            models.Index(fields=["chunk", "concept"]),
            models.Index(fields=["concept", "relevance_score"]),
        ]

    def __str__(self):
        return f"{self.chunk_id} -> {self.concept.name}"


class ConceptRelation(models.Model):
    source = models.ForeignKey(
        ConceptNode,
        on_delete=models.CASCADE,
        related_name="outgoing_relations",
    )
    target = models.ForeignKey(
        ConceptNode,
        on_delete=models.CASCADE,
        related_name="incoming_relations",
    )
    relation_type = models.CharField(max_length=50, default="relates_to")
    weight = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-weight", "source__name", "target__name"]
        unique_together = ("source", "target", "relation_type")
        indexes = [
            models.Index(fields=["source", "relation_type"]),
            models.Index(fields=["target", "relation_type"]),
        ]

    def __str__(self):
        return f"{self.source.name} -> {self.relation_type} -> {self.target.name}"


class ChunkEmbedding(models.Model):
    chunk = models.OneToOneField(
        PDFPageChunk,
        on_delete=models.CASCADE,
        related_name="embedding",
    )
    embedding_vector = models.JSONField(default=list)
    model_name = models.CharField(max_length=100, default="all-MiniLM-L6-v2")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["chunk_id"]
        indexes = [
            models.Index(fields=["model_name"]),
        ]

    def __str__(self):
        return f"Embedding for chunk {self.chunk_id}"


class GeneratedQuestion(models.Model):
    question = models.CharField(max_length=500)
    subject_code = models.CharField(max_length=50, db_index=True)
    concept = models.CharField(max_length=150, db_index=True)
    source_chunk = models.ForeignKey(
        PDFPageChunk,
        on_delete=models.CASCADE,
        related_name="generated_questions",
    )
    is_processed = models.BooleanField(default=False, db_index=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "generated_questions"
        ordering = ["is_processed", "-last_score", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "source_chunk"],
                name="unique_generated_question_per_chunk",
            )
        ]
        indexes = [
            models.Index(fields=["subject_code", "concept"], name="genq_subject_concept_idx"),
            models.Index(fields=["is_processed", "updated_at"], name="genq_process_state_idx"),
        ]

    def __str__(self):
        return self.question


class ConceptAnswerCache(models.Model):
    concept = models.CharField(max_length=150, unique=True)
    best_answer = models.TextField()
    references = models.JSONField(default=list, blank=True)
    confidence_score = models.FloatField(default=0.0)
    quality_score = models.PositiveSmallIntegerField(default=0)
    generation_mode = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "concept_answer_cache"
        ordering = ["-quality_score", "-confidence_score", "concept"]
        indexes = [
            models.Index(fields=["concept"], name="concept_cache_lookup_idx"),
            models.Index(fields=["quality_score", "confidence_score"], name="concept_cache_quality_idx"),
        ]

    def __str__(self):
        return self.concept


class ConceptRelationship(models.Model):
    concept = models.CharField(max_length=150, db_index=True)
    related_concept = models.CharField(max_length=150, db_index=True)
    relation_type = models.CharField(max_length=50, default="relates_to")
    weight = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "concept_relationships"
        ordering = ["-weight", "concept", "related_concept"]
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "related_concept", "relation_type"],
                name="unique_concept_relationship",
            )
        ]
        indexes = [
            models.Index(fields=["concept", "weight"], name="concept_rel_concept_idx"),
            models.Index(fields=["related_concept", "weight"], name="concept_rel_related_idx"),
        ]

    def __str__(self):
        return f"{self.concept} -> {self.related_concept}"


class RetrievalStrategyCache(models.Model):
    concept = models.CharField(max_length=150, unique=True)
    best_context_chunk_count = models.PositiveSmallIntegerField(default=5)
    best_keyword_weight = models.FloatField(default=0.7)
    best_semantic_weight = models.FloatField(default=0.3)
    best_rerank_strategy = models.CharField(max_length=50, default="semantic")
    confidence_score = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retrieval_strategy_cache"
        ordering = ["-confidence_score", "concept"]
        indexes = [
            models.Index(fields=["concept"], name="retr_strategy_concept_idx"),
            models.Index(fields=["confidence_score"], name="retr_strategy_conf_idx"),
        ]

    def __str__(self):
        return self.concept

