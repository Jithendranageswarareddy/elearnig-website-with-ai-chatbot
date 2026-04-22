import os
import re
import sys


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django  # noqa: E402


django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from courses.models import Subject, Unit  # noqa: E402
from chatbot.models import PDFPageChunk, ReferencePDF  # noqa: E402


FOCUS_SUBJECTS = [
    "Operating Systems",
    "Computer Networks",
    "Data Structures",
]

GARBAGE_PHRASES = [
    "this response is grounded",
    "the key point is",
    "this concept is explained in the syllabus context",
    "applied when a system uses clear rules",
    "seed minimal content",
    "detailed explanation",
    "disableconversionvalidationpdf",
]

UNIT_CONTENT = {
    "Operating Systems": {
        1: """
Operating System is system software that manages hardware resources and provides services to applications.
It acts as an interface between user programs and physical devices.
Core responsibilities include process execution, memory allocation, file handling, and device control.
The kernel schedules CPU time, handles interrupts, and enforces protection boundaries.
System calls allow programs to request OS services in a controlled way.
Modern operating systems support multitasking, multiuser access, and virtual memory.
Example: Linux coordinates CPU, RAM, disk, and network operations for browser, compiler, and database processes.
""".strip(),
        2: """
Process scheduling decides which ready process gets CPU time at a given moment.
A process moves through states such as ready, running, waiting, and terminated.
Schedulers optimize throughput, response time, turnaround time, and fairness.
Common policies are FCFS, SJF, Priority, and Round Robin.
Context switching saves and restores process state during CPU handoff.
Synchronization mechanisms like semaphores and mutexes prevent race conditions.
Example: Round Robin in time-sharing systems gives each process a fixed quantum for responsive interaction.
""".strip(),
        3: """
Memory management controls how primary memory is allocated and reclaimed.
Paging divides memory into fixed-size frames and processes into pages.
Segmentation organizes memory into logical units such as code, stack, and data.
Virtual memory allows execution of programs larger than physical RAM.
Page replacement algorithms include FIFO, LRU, and Optimal.
Thrashing occurs when excessive paging reduces useful CPU work.
Example: LRU keeps recently used pages in memory to reduce page faults for active applications.
""".strip(),
        4: """
File system organizes persistent data into files and directories.
It manages naming, metadata, block allocation, and access permissions.
Directory structures can be single-level, hierarchical, or graph-based.
Journaling improves reliability by recording metadata updates before commit.
Access methods include sequential and direct access.
Buffer cache improves performance by reducing physical disk reads.
Example: EXT4 journal recovery restores consistency after an unexpected power failure.
""".strip(),
        5: """
Deadlock is a condition where processes wait indefinitely for resources held by one another.
Necessary conditions are mutual exclusion, hold-and-wait, no preemption, and circular wait.
Strategies include prevention, avoidance, detection, and recovery.
Banker’s algorithm is a classic avoidance method based on safe-state checks.
Security in OS includes authentication, authorization, auditing, and isolation.
Principle of least privilege limits damage from compromised processes.
Example: Detecting circular wait in lock graphs helps recover from deadlock in database servers.
""".strip(),
    },
    "Computer Networks": {
        1: """
Computer network is a collection of interconnected devices that exchange data using protocols.
Network architecture is typically explained through layered models such as OSI and TCP/IP.
Physical and data link layers handle transmission and framing over media.
Addressing and routing deliver packets between hosts across multiple networks.
Performance metrics include bandwidth, latency, jitter, and packet loss.
Reliability is achieved using acknowledgments, retransmission, and flow control.
Example: A web request from a laptop to a cloud server uses Ethernet/Wi-Fi, IP routing, and TCP transport.
""".strip(),
        2: """
Data Link Layer provides node-to-node delivery over a single physical link.
It performs framing, MAC addressing, error detection, and medium access control.
Protocols such as Ethernet and PPP define frame format and link behavior.
CRC is widely used to detect transmission errors.
Switches forward frames based on MAC address tables.
VLANs logically segment LANs for security and traffic isolation.
Example: An Ethernet switch sends a frame only to the destination port using learned MAC mappings.
""".strip(),
        3: """
Network Layer provides logical addressing and path selection between networks.
IP packets are forwarded by routers according to routing tables.
Routing protocols such as OSPF and BGP exchange route information.
IP addressing supports subnetting and hierarchical network design.
TTL prevents infinite looping of packets.
ICMP helps with diagnostics and error reporting.
Example: Routers use longest-prefix matching to forward packets toward a destination subnet.
""".strip(),
        4: """
Transport Layer provides end-to-end communication between application processes.
TCP offers reliable, connection-oriented delivery with sequencing, acknowledgments, and retransmission.
UDP offers lightweight, connectionless delivery with low overhead.
Flow control and congestion control prevent sender overload and network collapse.
Port numbers identify destination services on a host.
Transport-layer protocols directly impact latency and reliability.
Example: Video calls often use UDP for low latency, while file transfers use TCP for reliable delivery.
""".strip(),
        5: """
Application Layer provides protocols used by end-user applications.
HTTP supports web communication, SMTP supports email transfer, and DNS resolves names to IP addresses.
Application protocols define message formats and service semantics.
Security is enhanced by TLS for encrypted sessions.
Client-server and peer-to-peer are common interaction models.
Caching and CDN usage improve response time for web content.
Example: A browser uses DNS to resolve a domain and then uses HTTPS to fetch page resources securely.
""".strip(),
    },
    "Data Structures": {
        1: """
Data structure is a way of organizing data for efficient access and modification.
Algorithm efficiency is commonly analyzed using time and space complexity.
Abstract Data Type separates behavior from implementation details.
Arrays, linked lists, stacks, and queues are foundational linear structures.
Choice of structure depends on operation patterns like insert, delete, and search.
Recursion and iteration are common techniques for traversal and problem solving.
Example: Arrays provide O(1) index access, while linked lists support flexible insertions.
""".strip(),
        2: """
Stack is a linear data structure that follows Last-In-First-Out order.
Queue is a linear data structure that follows First-In-First-Out order.
Operations include push/pop for stack and enqueue/dequeue for queue.
Recursion implicitly uses a call stack to store activation records.
Searching techniques include linear search and binary search.
Binary search requires sorted data and reduces search space by half each step.
Example: Browser back navigation uses a stack, while printer job processing uses a queue.
""".strip(),
        3: """
Tree is a hierarchical data structure with parent-child relationships.
Binary Search Tree supports ordered search, insert, and delete operations.
Traversal methods include preorder, inorder, and postorder.
Hash tables provide average O(1) lookup via key hashing.
Collision handling can use chaining or open addressing.
Balanced trees improve worst-case performance for dynamic sets.
Example: Database indexes use tree structures to speed up range and equality queries.
""".strip(),
        4: """
Graph represents entities as vertices and relationships as edges.
Graphs can be directed or undirected, weighted or unweighted.
Breadth-First Search finds shortest path in unweighted graphs.
Depth-First Search is useful for cycle detection and topological analysis.
Minimum spanning tree and shortest path are key optimization problems.
Dijkstra’s algorithm computes shortest paths in non-negative weighted graphs.
Example: Navigation systems model cities and roads as weighted graphs for route planning.
""".strip(),
        5: """
Data structures are applied in compilers, operating systems, databases, and networks.
Priority queues support scheduling and event-driven simulation.
Trie supports fast prefix queries for dictionaries and autocomplete.
Disjoint set supports efficient union-find operations in connectivity problems.
Selecting the right data structure improves scalability and maintainability.
Real-world systems combine multiple structures for performance goals.
Example: Search engines use hash maps, tries, and graphs together to process queries efficiently.
""".strip(),
    },
}


def normalize_text(text):
    value = str(text or "")
    value = value.replace("\u00ad", "")
    value = re.sub(r"\b\d{2}[A-Z]{2}\d[TP]\d{2}\b", "", value)
    value = re.sub(r"\bUnit\s+\d+\s*:\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+[\u2013-]\s+", " - ", value)
    lowered = value.lower()
    for phrase in GARBAGE_PHRASES:
        lowered = lowered.replace(phrase, "")
    value = lowered
    value = re.sub(r"(?i)\bintroduction\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", value) if s.strip()]
    unique = []
    seen = set()
    for sentence in sentences:
        key = re.sub(r"\s+", " ", sentence.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(sentence)
    return " ".join(unique).strip()


def ensure_focus_unit_content():
    updated = 0
    for subject_name, by_unit in UNIT_CONTENT.items():
        subject = Subject.objects.filter(name__iexact=subject_name).first()
        if not subject:
            continue
        for unit_number, content in by_unit.items():
            unit = Unit.objects.filter(subject=subject, unit_number=unit_number).first()
            if not unit:
                continue
            normalized = normalize_text(content)
            if unit.content != normalized:
                unit.content = normalized
                unit.save(update_fields=["content"])
                updated += 1
    return updated


def deactivate_seed_pdfs():
    qs = ReferencePDF.objects.filter(
        is_active=True,
        title__iregex=r"seed minimal content|disableconversionvalidationpdf",
    )
    count = qs.count()
    if count:
        qs.update(is_active=False)
    return count


def ensure_cn_reference_data():
    cn_subject = Subject.objects.filter(name__iexact="Computer Networks").first()
    if not cn_subject:
        return 0, 0

    user_model = get_user_model()
    uploader = (
        user_model.objects.filter(is_superuser=True).first()
        or user_model.objects.filter(is_staff=True).first()
        or user_model.objects.first()
    )
    if not uploader:
        return 0, 0

    fallback_pdf = ReferencePDF.objects.filter(is_active=True).exclude(file="").first()
    fallback_file_name = fallback_pdf.file.name if fallback_pdf and fallback_pdf.file else "pdfs/placeholder.pdf"

    cn_pdf, created = ReferencePDF.objects.get_or_create(
        subject=cn_subject,
        title="20CS4T04 - Computer Networks",
        defaults={
            "uploaded_by": uploader,
            "file": fallback_file_name,
            "is_syllabus_reference": True,
            "status": ReferencePDF.Status.APPROVED,
            "is_active": True,
            "processing_status": ReferencePDF.ProcessingStatus.READY,
            "extracted_text": " ".join(UNIT_CONTENT["Computer Networks"].values()),
        },
    )

    chunks_added = 0
    for index, unit_number in enumerate(sorted(UNIT_CONTENT["Computer Networks"].keys()), start=1):
        unit = Unit.objects.filter(subject=cn_subject, unit_number=unit_number).first()
        text = UNIT_CONTENT["Computer Networks"][unit_number]
        cleaned = normalize_text(text)
        chunk, chunk_created = PDFPageChunk.objects.get_or_create(
            reference_pdf=cn_pdf,
            page_number=index,
            chunk_index=0,
            defaults={
                "text_content": cleaned,
                "metadata": {
                    "subject": "Computer Networks",
                    "unit_number": unit_number,
                    "unit_title": unit.title if unit else f"Unit {unit_number}",
                },
            },
        )
        if not chunk_created and chunk.text_content != cleaned:
            chunk.text_content = cleaned
            chunk.metadata = {
                "subject": "Computer Networks",
                "unit_number": unit_number,
                "unit_title": unit.title if unit else f"Unit {unit_number}",
            }
            chunk.save(update_fields=["text_content", "metadata"])
        if chunk_created:
            chunks_added += 1

    cn_pdf.chunk_count = PDFPageChunk.objects.filter(reference_pdf=cn_pdf).count()
    cn_pdf.processing_status = ReferencePDF.ProcessingStatus.READY
    cn_pdf.is_active = True
    cn_pdf.status = ReferencePDF.Status.APPROVED
    cn_pdf.is_syllabus_reference = True
    cn_pdf.save(update_fields=["chunk_count", "processing_status", "is_active", "status", "is_syllabus_reference"])

    return int(created), chunks_added


def clean_focus_chunks():
    subjects = Subject.objects.filter(name__in=FOCUS_SUBJECTS)
    qs = PDFPageChunk.objects.filter(reference_pdf__subject__in=subjects, reference_pdf__is_active=True).select_related(
        "reference_pdf",
        "reference_pdf__subject",
    )
    updated = 0
    for chunk in qs:
        cleaned = normalize_text(chunk.text_content)
        if cleaned and cleaned != (chunk.text_content or ""):
            chunk.text_content = cleaned
            chunk.save(update_fields=["text_content"])
            updated += 1
    return updated


def main():
    updated_units = ensure_focus_unit_content()
    deactivated_seed = deactivate_seed_pdfs()
    cn_pdf_created, cn_chunks_added = ensure_cn_reference_data()
    cleaned_chunks = clean_focus_chunks()

    print("=== FINAL DATA QUALITY UPGRADE REPORT ===")
    print(f"Updated unit content rows: {updated_units}")
    print(f"Deactivated seed/validation PDFs: {deactivated_seed}")
    print(f"Computer Networks reference PDF created: {cn_pdf_created}")
    print(f"Computer Networks chunks added: {cn_chunks_added}")
    print(f"Cleaned focus-subject chunks: {cleaned_chunks}")


if __name__ == "__main__":
    main()
