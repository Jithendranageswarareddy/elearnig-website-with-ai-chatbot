import hashlib
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.utils.text import slugify  # noqa: E402

from accounts.models import User  # noqa: E402
from chatbot.models import PDFPageChunk, ReferencePDF  # noqa: E402
from chatbot.services.embedding_service import store_chunk_embeddings  # noqa: E402
from courses.models import Semester, Subject  # noqa: E402


DEMO_CORPUS = [
    {
        "subject_code": "OOP401",
        "subject_name": "Object-Oriented Programming",
        "title": "OOP Foundations Demo Syllabus",
        "pages": [
            [
                "Polymorphism allows one interface to support many concrete behaviors in object oriented programming. The syllabus defines runtime polymorphism as method overriding resolved through inheritance.",
                "Inheritance establishes the common parent-child relationship used to enable polymorphic method dispatch in class hierarchies.",
                "Figure 1 shows the class hierarchy architecture for polymorphism, method overriding, and dynamic binding.",
            ],
            [
                "Method overloading and method overriding are distinct. Overloading changes the parameter list while overriding replaces inherited behavior in a subclass.",
                "Example: a drawing system can call draw on many shapes, and each subclass supplies its own implementation.",
            ],
            [
                "Abstraction and encapsulation usually appear with polymorphism because the syllabus groups them as core object oriented principles.",
                "The review section emphasizes related concepts such as dynamic binding, inheritance, and interface design.",
            ],
        ],
        "diagrams": [
            {
                "page_number": 1,
                "title": "Polymorphism Hierarchy",
                "subtitle": "Class hierarchy and method dispatch",
                "nodes": ["Base Class", "Circle", "Rectangle"],
            },
        ],
    },
    {
        "subject_code": "DS301",
        "subject_name": "Data Structures",
        "title": "Data Structures Demo Syllabus",
        "pages": [
            [
                "A stack is a linear data structure following last in first out order. Push inserts an element and pop removes the most recent element.",
                "Queue operations follow first in first out order and provide a useful comparison with stack behavior in exam answers.",
            ],
            [
                "Binary tree traversal visits nodes in a defined sequence. Preorder processes root-left-right, inorder processes left-root-right, and postorder processes left-right-root.",
                "Figure 2 presents the binary tree traversal structure and the visit order used in recursive algorithms.",
                "Example: inorder traversal of a binary search tree lists the keys in sorted order.",
            ],
            [
                "Breadth first search explores a tree level by level, while depth first search follows one branch until backtracking occurs.",
                "The syllabus revision notes relate traversal algorithms to recursion, queue usage, and tree hierarchy diagrams.",
            ],
        ],
        "diagrams": [
            {
                "page_number": 2,
                "title": "Binary Tree Traversal",
                "subtitle": "Traversal order for root and child nodes",
                "nodes": ["Root", "Left", "Right"],
            },
        ],
    },
    {
        "subject_code": "OS302",
        "subject_name": "Operating Systems",
        "title": "Operating Systems Demo Syllabus",
        "pages": [
            [
                "A process memory layout typically includes code, data, heap, and stack regions. The stack stores function call frames, parameters, and return addresses.",
                "The architecture section explains how stack growth differs from heap growth in a process address space.",
            ],
            [
                "Stack overflow occurs when nested calls or large local allocations exceed the configured stack region. The syllabus describes the fault as a memory protection failure during execution.",
                "Figure 3 shows the stack growth flowchart, the overflow boundary, and the exception raised after the stack limit is crossed.",
                "Example: uncontrolled recursion can trigger stack overflow because each call pushes another frame onto the stack.",
            ],
            [
                "Context switching saves process state so that the scheduler can resume another process. Scheduling notes relate process control blocks, ready queues, and CPU allocation.",
                "Students are expected to compare recursion depth, stack frames, and exception handling in system programming questions.",
            ],
        ],
        "diagrams": [
            {
                "page_number": 2,
                "title": "Stack Overflow Flow",
                "subtitle": "Stack limit crossing during recursion",
                "nodes": ["Function Call", "Stack Frame", "Limit", "Fault"],
            },
        ],
    },
    {
        "subject_code": "DB303",
        "subject_name": "Database Systems",
        "title": "Database Systems Demo Syllabus",
        "pages": [
            [
                "Normalization organizes relational data to reduce redundancy and update anomalies. First normal form removes repeating groups and higher forms reduce partial or transitive dependency.",
                "The syllabus defines normalization as a design discipline for clean relational schemas and dependable transactions.",
            ],
            [
                "A database architecture diagram usually includes clients, the query processor, the storage manager, and the data files.",
                "Figure 4 shows the database system structure and the flow from SQL request to disk pages through buffer management.",
            ],
            [
                "B-tree indexing improves search performance by reducing the number of disk accesses required to locate ordered keys.",
                "Transactions preserve consistency through atomicity, consistency, isolation, and durability.",
            ],
        ],
        "diagrams": [
            {
                "page_number": 2,
                "title": "Database System Structure",
                "subtitle": "Client, query processor, storage manager, and disk files",
                "nodes": ["Client", "Query Processor", "Storage Manager", "Disk"],
            },
        ],
    },
]


def _escape_pdf_text(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_lines(title, paragraphs):
    lines = [title, ""]
    for paragraph in paragraphs:
        words = paragraph.split()
        current = []
        current_length = 0
        for word in words:
            addition = len(word) + (1 if current else 0)
            if current_length + addition > 86:
                lines.append(" ".join(current))
                current = [word]
                current_length = len(word)
            else:
                current.append(word)
                current_length += addition
        if current:
            lines.append(" ".join(current))
        lines.append("")
    return lines


def _pdf_stream_for_page(title, paragraphs):
    lines = _page_lines(title, paragraphs)
    commands = [
        "BT",
        "/F1 16 Tf",
        "72 760 Td",
        "18 TL",
    ]
    for index, line in enumerate(lines):
        if index == 0:
            commands.append(f"({_escape_pdf_text(line)}) Tj")
        else:
            commands.append("T*")
            if line:
                commands.append(f"({_escape_pdf_text(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", "replace")


def _build_pdf_bytes(title, pages):
    objects = [None, "<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_ids = []

    for paragraphs in pages:
        content_bytes = _pdf_stream_for_page(title, paragraphs)
        content_id = len(objects)
        objects.append(f"<< /Length {len(content_bytes)} >>\nstream\n{content_bytes.decode('latin-1')}\nendstream")
        page_id = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[2] = f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>"

    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    cursor = len(chunks[0])
    for object_id in range(1, len(objects)):
        body = f"{object_id} 0 obj\n{objects[object_id]}\nendobj\n".encode("latin-1")
        offsets.append(cursor)
        chunks.append(body)
        cursor += len(body)

    xref_start = cursor
    chunks.append(f"xref\n0 {len(objects)}\n".encode("latin-1"))
    chunks.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        chunks.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
    chunks.append(f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("latin-1"))
    return b"".join(chunks)


def _diagram_svg(title, subtitle, nodes):
    boxes = []
    x = 50
    for node in nodes:
        boxes.append(
            f'<rect x="{x}" y="110" width="150" height="54" rx="18" fill="#f5f8ff" stroke="#2260ee" stroke-width="2"/>'
            f'<text x="{x + 75}" y="142" text-anchor="middle" font-family="Manrope, Arial, sans-serif" font-size="16" fill="#122038">{node}</text>'
        )
        x += 170
    arrows = []
    for index in range(len(nodes) - 1):
        start_x = 200 + (index * 170)
        arrows.append(
            f'<line x1="{start_x}" y1="137" x2="{start_x + 20}" y2="137" stroke="#12b8b5" stroke-width="4" stroke-linecap="round"/>'
            f'<polygon points="{start_x + 20},137 {start_x + 6},129 {start_x + 6},145" fill="#12b8b5"/>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="260" viewBox="0 0 760 260">
<rect width="760" height="260" rx="28" fill="#ffffff"/>
<rect x="20" y="20" width="720" height="220" rx="24" fill="#eef4ff" stroke="#cfe0ff"/>
<text x="40" y="60" font-family="Manrope, Arial, sans-serif" font-size="28" font-weight="700" fill="#122038">{title}</text>
<text x="40" y="88" font-family="Manrope, Arial, sans-serif" font-size="16" fill="#3e4f70">{subtitle}</text>
{''.join(boxes)}
{''.join(arrows)}
</svg>"""


def _save_media_file(relative_path, content_bytes):
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(content_bytes)
    return relative_path.replace("\\", "/")


def _diagram_path(slug, page_number):
    return f"pdf_images/demo_{slug}_page_{page_number}.svg"


def _pdf_path(slug):
    return f"pdfs/demo_{slug}.pdf"


def _demo_faculty():
    faculty, created = User.objects.get_or_create(
        email="demo.faculty@example.com",
        defaults={
            "name": "Demo Faculty",
            "role": User.Role.FACULTY,
        },
    )
    if created:
        faculty.set_password("demo12345")
        faculty.save(update_fields=["password"])
    return faculty


def _demo_semester():
    semester, _created = Semester.objects.update_or_create(
        number=6,
        regulation="DEMO-2026",
        defaults={
            "description": "Demo semester for final project walkthroughs",
            "is_active": True,
        },
    )
    return semester


def main():
    faculty = _demo_faculty()
    semester = _demo_semester()
    now = timezone.now()
    created_titles = []

    for item in DEMO_CORPUS:
        subject, _ = Subject.objects.update_or_create(
            semester=semester,
            subject_code=item["subject_code"],
            defaults={
                "name": item["subject_name"],
                "description": f"Demo subject for {item['subject_name']}",
                "is_active": True,
            },
        )

        slug = slugify(item["title"])
        pdf_bytes = _build_pdf_bytes(item["title"], item["pages"])
        pdf_relative_path = _save_media_file(_pdf_path(slug), pdf_bytes)

        reference_pdf, _ = ReferencePDF.objects.update_or_create(
            subject=subject,
            title=item["title"],
            defaults={
                "uploaded_by": faculty,
                "file": pdf_relative_path,
                "extracted_text": "",
                "is_syllabus_reference": True,
                "status": ReferencePDF.Status.APPROVED,
                "is_active": True,
                "processing_status": ReferencePDF.ProcessingStatus.READY,
                "processing_error": "",
                "last_processed_at": now,
            },
        )
        if reference_pdf.file.name != pdf_relative_path:
            reference_pdf.file.name = pdf_relative_path

        PDFPageChunk.objects.filter(reference_pdf=reference_pdf).delete()

        extracted_pages = []
        chunk_rows = []
        for page_number, paragraphs in enumerate(item["pages"], start=1):
            extracted_pages.append("\n\n".join(paragraphs))
            for chunk_index, paragraph in enumerate(paragraphs):
                chunk_rows.append(
                    PDFPageChunk(
                        reference_pdf=reference_pdf,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        text_content=paragraph,
                        metadata={
                            "source": "demo_seed",
                            "paragraph_index": chunk_index,
                            "chunk_length": len(paragraph),
                            "token_count": len(paragraph.split()),
                            "page_preview": paragraph[:100],
                        },
                    )
                )
        PDFPageChunk.objects.bulk_create(chunk_rows)
        created_chunks = list(
            PDFPageChunk.objects.filter(reference_pdf=reference_pdf).only("id", "text_content")
        )
        store_chunk_embeddings(created_chunks)

        reference_pdf.extracted_text = "\n\n".join(extracted_pages)
        reference_pdf.chunk_count = len(chunk_rows)
        reference_pdf.processing_status = ReferencePDF.ProcessingStatus.READY
        reference_pdf.processing_error = ""
        reference_pdf.last_processed_at = now
        reference_pdf.save(
            update_fields=[
                "file",
                "extracted_text",
                "chunk_count",
                "diagram_count",
                "processing_status",
                "processing_error",
                "last_processed_at",
                "uploaded_by",
                "is_syllabus_reference",
                "status",
                "is_active",
            ]
        )
        created_titles.append(reference_pdf.title)

    print("Demo dataset ready.")
    for title in created_titles:
        print(f"- {title}")
    print("Subjects seeded:", ", ".join(item["subject_name"] for item in DEMO_CORPUS))


if __name__ == "__main__":
    main()
