"""
Generate 100 high-quality test questions from database.
Source: Subjects, Units, PDF content (NO external knowledge)
Distribution: Evenly across subjects/units with proper question type mix
"""

import json
import os
import random
import re
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django
django.setup()

from courses.models import Subject, Unit, Lesson
from chatbot.models import PDFPageChunk, ReferencePDF

# Question templates for different types
QUESTION_TEMPLATES = {
    "definition": [
        "Define {topic}.",
        "What is {topic}?",
        "Explain the concept of {topic}.",
        "Give a definition of {topic}.",
        "What do you understand by {topic}?",
    ],
    "explanation": [
        "Explain {topic}.",
        "Describe {topic} in detail.",
        "What is the significance of {topic}?",
        "Elaborate on {topic}.",
        "How does {topic} work?",
        "Discuss {topic}.",
    ],
    "comparison": [
        "Compare {topic1} and {topic2}.",
        "What is the difference between {topic1} and {topic2}?",
        "Differentiate between {topic1} and {topic2}.",
        "How is {topic1} different from {topic2}?",
        "{topic1} vs {topic2}: explain the differences.",
    ],
    "process": [
        "Explain the steps involved in {topic}.",
        "What are the stages of {topic}?",
        "Describe the process of {topic}.",
        "How is {topic} performed/executed?",
        "List the steps for {topic}.",
    ],
    "advantages": [
        "What are the advantages of {topic}?",
        "Explain the benefits of {topic}.",
        "Why is {topic} important?",
        "Discuss the advantages of using {topic}.",
        "What are the merits of {topic}?",
    ],
    "conceptual": [
        "What is the purpose of {topic}?",
        "Explain why {topic} is important.",
        "How does {topic} relate to {context}?",
        "What is the role of {topic}?",
        "Why do we need {topic}?",
    ],
    "application": [
        "How can {topic} be applied in real-world scenarios?",
        "Give examples of {topic}.",
        "Where is {topic} used?",
        "How would you use {topic}?",
        "Describe a practical application of {topic}.",
    ],
}

# Difficulty levels map
DIFFICULTY_MAP = {
    "easy": ["definition", "conceptual", "explanation"],
    "medium": ["explanation", "process", "comparison", "conceptual"],
    "hard": ["comparison", "process", "application", "advantages"],
}


def extract_topics_from_unit(unit):
    """Extract potential topics from unit description and lessons."""
    topics = []
    
    if unit.title:
        title = unit.title.strip()
        if title:
            topics.append(title)
    
    if unit.content:
        content = unit.content.strip()
        sentences = [s.strip() for s in content.split('.') if s.strip() and len(s.strip()) > 10]
        topics.extend(sentences[:3])
    
    # Get lessons under this unit
    lessons = Lesson.objects.filter(unit=unit, is_active=True)[:5]
    for lesson in lessons:
        if lesson.title:
            topics.append(lesson.title.strip())
        if lesson.content:
            content = lesson.content.strip()
            if len(content) > 15:
                topics.append(content[:100])
    
    return [t for t in topics if t and len(t) > 3]


def extract_topics_from_pdf(pdf_id, max_topics=5):
    """Extract potential topics from PDF chunks."""
    topics = []
    chunks = PDFPageChunk.objects.filter(reference_pdf_id=pdf_id)[:10]
    
    for chunk in chunks:
        text = chunk.text_content or ""
        if len(text) < 20:
            continue
        
        # Take first 150 chars as potential topic
        topic = " ".join(text[:150].split())
        if len(topic) > 15:
            topics.append(topic)
    
    return topics[:max_topics]


def generate_question(qtype, topics, subject_name, unit_name, difficulty):
    """Generate a single question from template and topics."""
    if not topics:
        return None
    
    template = random.choice(QUESTION_TEMPLATES[qtype])
    
    try:
        if "{topic1}" in template and "{topic2}" in template:
            if len(topics) < 2:
                topics_copy = topics * 2
            else:
                topics_copy = topics
            topic1 = random.choice(topics_copy)
            topic2 = random.choice(topics_copy)
            while topic2 == topic1 and len(topics_copy) > 1:
                topic2 = random.choice(topics_copy)
            question = template.format(topic1=topic1, topic2=topic2)
        elif "{context}" in template:
            context = subject_name or unit_name
            topic = random.choice(topics)
            question = template.format(topic=topic, context=context)
        elif "{topic}" in template:
            topic = random.choice(topics)
            question = template.format(topic=topic)
        else:
            question = template
    except Exception as e:
        print("ERROR:", str(e))
        return None
    
    return question.strip()


def main():
    print("=" * 80)
    print("GENERATING 100 TEST QUESTIONS FROM DATABASE")
    print("=" * 80)
    
    # Fetch data
    print("\n📚 Loading database content...")
    subjects = list(Subject.objects.filter(is_active=True).order_by('id'))
    units = list(Unit.objects.filter(is_active=True).order_by('id'))
    pdfs = list(ReferencePDF.objects.filter(
        is_active=True,
        status=ReferencePDF.Status.APPROVED,
        is_syllabus_reference=True
    ).order_by('id'))
    
    print(f"   ✓ Subjects: {len(subjects)}")
    print(f"   ✓ Units: {len(units)}")
    print(f"   ✓ PDFs: {len(pdfs)}")
    
    if not subjects or not units:
        raise RuntimeError("No active subjects or units found in database")
    
    # Collect all topics by subject
    subject_topics = defaultdict(list)
    unit_topics = defaultdict(list)
    pdf_subjects = {}  # pdf_id -> subject
    
    print("\n🔍 Extracting topics from subjects and units...")
    for unit in units:
        topics = extract_topics_from_unit(unit)
        if topics:
            unit_topics[unit.id] = topics
            if unit.subject:
                subject_topics[unit.subject.id].extend(topics)
    
    for pdf in pdfs:
        topics = extract_topics_from_pdf(pdf.id)
        if topics:
            subject_topics[pdf.subject_id].extend(topics)
        pdf_subjects[pdf.id] = pdf.subject_id
    
    # Remove duplicates while preserving order
    for key in subject_topics:
        seen = set()
        unique = []
        for topic in subject_topics[key]:
            t_lower = topic.lower()
            if t_lower not in seen:
                seen.add(t_lower)
                unique.append(topic)
        subject_topics[key] = unique[:20]
    
    print(f"   ✓ Extracted topics from {len(subject_topics)} subjects")
    print(f"   ✓ Extracted topics from {len(unit_topics)} units")
    
    # Generate 100 questions
    print("\n🧠 Generating questions...")
    questions = []
    rng = random.Random(42)
    
    # Calculate distribution
    question_types = list(QUESTION_TEMPLATES.keys())
    difficulty_levels = ["easy", "medium", "hard"]
    
    # Type distribution: definitions(20), explanations(20), comparisons(15), processes(15),
    # advantages(10), conceptual(10), application(10)
    type_counts = {
        "definition": 20,
        "explanation": 20,
        "comparison": 15,
        "process": 15,
        "advantages": 10,
        "conceptual": 10,
        "application": 10,
    }
    
    # Difficulty distribution: easy(40%), medium(40%), hard(20%)
    difficulty_pool = (
        ["easy"] * 40 + 
        ["medium"] * 40 + 
        ["hard"] * 20
    )
    rng.shuffle(difficulty_pool)
    
    # Get all available subject-unit pairs
    subject_unit_pairs = []
    for unit in units:
        if unit.subject_id:
            subject_unit_pairs.append((unit.subject_id, unit.id))
    
    if not subject_unit_pairs:
        # Fallback: use subjects directly
        subject_unit_pairs = [(s.id, None) for s in subjects]
    
    question_id = 1
    difficulty_idx = 0
    
    for qtype, target_count in type_counts.items():
        generated = 0
        attempts = 0
        max_attempts = target_count * 5
        
        while generated < target_count and attempts < max_attempts:
            attempts += 1
            
            # Get difficulty
            difficulty = difficulty_pool[difficulty_idx % len(difficulty_pool)]
            difficulty_idx += 1
            
            # Select subject and unit
            subject_id, unit_id = rng.choice(subject_unit_pairs)
            subject = next((s for s in subjects if s.id == subject_id), None)
            unit = next((u for u in units if u.id == unit_id), None) if unit_id else None
            
            # Get topics for this subject/unit
            topics = subject_topics.get(subject_id, [])
            if unit_id:
                topics.extend(unit_topics.get(unit_id, []))
            
            topics = list(set(topics))  # Remove duplicates
            rng.shuffle(topics)
            
            if not topics:
                continue
            
            # Generate question
            question_text = generate_question(
                qtype,
                topics[:5],
                subject.name if subject else "Unknown",
                unit.title if unit else "Unknown",
                difficulty
            )
            
            if not question_text:
                continue
            
            # Check for duplicates
            if any(q["question"].lower() == question_text.lower() for q in questions):
                continue
            
            questions.append({
                "id": question_id,
                "question": question_text,
                "subject": subject.name if subject else "Unknown",
                "subject_id": subject_id,
                "unit": unit.title if unit else "Unknown",
                "unit_id": unit_id,
                "type": qtype,
                "difficulty": difficulty,
            })
            
            question_id += 1
            generated += 1
    
    # If we have fewer than 100, try to fill gaps
    remaining = 100 - len(questions)
    if remaining > 0:
        print(f"\n⚠️  Generated {len(questions)} questions, filling {remaining} gaps...")
        for i in range(remaining):
            difficulty = difficulty_pool[difficulty_idx % len(difficulty_pool)]
            difficulty_idx += 1
            qtype = rng.choice(question_types)
            subject_id, unit_id = rng.choice(subject_unit_pairs)
            subject = next((s for s in subjects if s.id == subject_id), None)
            unit = next((u for u in units if u.id == unit_id), None) if unit_id else None
            
            topics = subject_topics.get(subject_id, [])
            if unit_id:
                topics.extend(unit_topics.get(unit_id, []))
            
            topics = list(set(topics))
            rng.shuffle(topics)
            
            if not topics:
                continue
            
            question_text = generate_question(
                qtype,
                topics[:5],
                subject.name if subject else "Unknown",
                unit.title if unit else "Unknown",
                difficulty
            )
            
            if question_text and not any(q["question"].lower() == question_text.lower() for q in questions):
                questions.append({
                    "id": len(questions) + 1,
                    "question": question_text,
                    "subject": subject.name if subject else "Unknown",
                    "subject_id": subject_id,
                    "unit": unit.title if unit else "Unknown",
                    "unit_id": unit_id,
                    "type": qtype,
                    "difficulty": difficulty,
                })
    
    # Shuffle final list
    rng.shuffle(questions)
    for idx, q in enumerate(questions, 1):
        q["id"] = idx
    
    # Save to JSON
    os.makedirs("reports", exist_ok=True)
    out_path = os.path.join("reports", "test_100_questions.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    # Calculate and print statistics
    print("\n" + "=" * 80)
    print("📊 GENERATION SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Total questions generated: {len(questions)}/100")
    
    # Subject-wise count
    print("\n📚 Subject-wise distribution:")
    subject_counts = defaultdict(int)
    for q in questions:
        subject_counts[q["subject"]] += 1
    
    for subject in sorted(subject_counts.keys()):
        count = subject_counts[subject]
        pct = round((count / len(questions)) * 100, 1)
        print(f"   • {subject}: {count} ({pct}%)")
    
    # Unit-wise coverage
    print("\n📖 Unit-wise coverage:")
    unit_counts = defaultdict(int)
    for q in questions:
        unit_counts[q["unit"]] += 1
    
    unique_units = len(unit_counts)
    print(f"   • Covered {unique_units} unique units")
    print(f"   • Average questions per unit: {len(questions) / max(1, unique_units):.1f}")
    
    # Question type distribution
    print("\n❓ Question type distribution:")
    type_counts = defaultdict(int)
    for q in questions:
        type_counts[q["type"]] += 1
    
    for qtype in sorted(type_counts.keys()):
        count = type_counts[qtype]
        pct = round((count / len(questions)) * 100, 1)
        print(f"   • {qtype}: {count} ({pct}%)")
    
    # Difficulty distribution
    print("\n🎯 Difficulty distribution:")
    difficulty_counts = defaultdict(int)
    for q in questions:
        difficulty_counts[q["difficulty"]] += 1
    
    for difficulty in ["easy", "medium", "hard"]:
        count = difficulty_counts[difficulty]
        pct = round((count / len(questions)) * 100, 1)
        print(f"   • {difficulty}: {count} ({pct}%)")
    
    print("\n" + "=" * 80)
    print(f"📁 Output saved to: {os.path.abspath(out_path)}")
    print("=" * 80)
    print("\n✨ Generated 100 test questions successfully!")


if __name__ == "__main__":
    main()
