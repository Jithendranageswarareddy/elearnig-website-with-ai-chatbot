import os
import sys
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")
os.chdir(ROOT)
django.setup()

from courses.models import Subject, Unit, Lesson  # noqa: E402

DATA = {
    "20CS3T02": {
        1: {
            "title": "Unit 1: Logic and Proof Techniques",
            "content": """### UNIT 1: Logic and Proof Techniques

#### Introduction

Logic forms the foundation of mathematical reasoning and computer science. It provides a formal framework for representing and analyzing statements, enabling the development of correct algorithms and systems. This unit introduces propositional logic, logical equivalences, and various proof techniques used to validate mathematical statements.

Understanding logic is essential for designing algorithms, verifying correctness, and building reliable software systems. Proof techniques help in establishing the validity of statements through structured reasoning.

#### Detailed Explanation

**Propositional Logic**
Propositional logic deals with statements that are either true or false. Logical operators such as AND, OR, NOT, implication, and biconditional are used to form complex expressions. Truth tables are used to evaluate these expressions.

For example, a statement like "If it rains, then the ground is wet" can be represented using logical implication.

**Logical Equivalences**
Logical equivalences allow the transformation of logical expressions into simpler or alternative forms. Laws such as De Morgan’s laws and distributive laws are commonly used.

These equivalences are important in simplifying expressions and optimizing logical circuits.

**Proof Techniques**
Proof techniques include direct proof, proof by contradiction, and mathematical induction.

For instance, proof by induction is used to prove statements involving natural numbers by verifying a base case and an inductive step.

#### Applications

Logic and proof techniques are used in algorithm design, software verification, artificial intelligence, and digital circuit design.

#### Summary

This unit introduces logical reasoning and proof techniques, which are essential for mathematical rigor and computational problem solving.""",
        },
        2: {
            "title": "Unit 2: Set Theory and Relations",
            "content": """### UNIT 2: Set Theory and Relations

#### Introduction

Set theory is a fundamental concept in mathematics that deals with collections of objects. Relations describe how elements of sets are connected. This unit introduces sets, operations on sets, and different types of relations.

These concepts are widely used in database systems, logic, and computer science applications.

#### Detailed Explanation

**Sets and Operations**
A set is a collection of distinct elements. Operations such as union, intersection, difference, and complement are used to manipulate sets.

For example, the union of two sets combines all elements from both sets.

**Relations**
A relation is a subset of the Cartesian product of two sets. Relations can be reflexive, symmetric, and transitive.

These properties determine the nature of relationships between elements.

**Equivalence Relations and Functions**
Equivalence relations partition sets into equivalence classes. Functions map elements from one set to another, ensuring each input has a unique output.

#### Applications

Set theory and relations are used in databases, programming languages, and formal systems. They are essential for modeling relationships and data structures.

#### Summary

This unit covers sets, operations, and relations, providing a basis for understanding mathematical structures in computing.""",
        },
        3: {
            "title": "Unit 3: Combinatorics",
            "content": """### UNIT 3: Combinatorics

#### Introduction

Combinatorics deals with counting, arrangement, and selection of objects. It is essential in analyzing algorithms and solving problems involving permutations and combinations.

This unit introduces basic counting principles and combinatorial techniques.

#### Detailed Explanation

**Counting Principles**
The fundamental counting principle states that if one task can be done in m ways and another in n ways, then both tasks can be done in m × n ways.

This principle is widely used in problem solving.

**Permutations and Combinations**
Permutations deal with arrangements where order matters, while combinations deal with selections where order does not matter.

For example, arranging books on a shelf is a permutation, while selecting a team is a combination.

**Binomial Theorem**
The binomial theorem provides a formula for expanding expressions raised to a power. It is closely related to combinations.

#### Applications

Combinatorics is used in probability, cryptography, algorithm design, and network analysis.

#### Summary

This unit introduces counting techniques, permutations, and combinations, which are essential for problem solving in computer science.""",
        },
        4: {
            "title": "Unit 4: Graph Theory",
            "content": """### UNIT 4: Graph Theory

#### Introduction

Graph theory studies structures used to model pairwise relationships between objects. Graphs consist of vertices and edges and are widely used in computer science.

This unit introduces types of graphs and their properties.

#### Detailed Explanation

**Basic Concepts of Graphs**
A graph consists of vertices (nodes) and edges (connections). Graphs can be directed or undirected.

For example, a social network can be represented as a graph.

**Graph Traversal**
Traversal techniques such as Depth First Search (DFS) and Breadth First Search (BFS) are used to explore graphs.

These algorithms are essential for searching and pathfinding.

**Shortest Path Algorithms**
Algorithms like Dijkstra’s algorithm find the shortest path between nodes in a graph.

#### Applications

Graph theory is used in networking, routing, social networks, and artificial intelligence.

#### Summary

This unit introduces graph structures and algorithms, which are essential for modeling relationships and solving complex problems.""",
        },
        5: {
            "title": "Unit 5: Algebraic Structures",
            "content": """### UNIT 5: Algebraic Structures

#### Introduction

Algebraic structures provide a framework for studying sets with operations. They are fundamental in abstract mathematics and computer science.

This unit introduces groups, rings, and fields.

#### Detailed Explanation

**Groups**
A group is a set with a binary operation that satisfies closure, associativity, identity, and invertibility.

Groups are used in cryptography and symmetry analysis.

**Rings and Fields**
Rings extend groups with additional operations, while fields provide a complete structure for arithmetic operations.

For example, real numbers form a field.

#### Applications

Algebraic structures are used in coding theory, cryptography, and algorithm design.

#### Summary

This unit introduces algebraic structures, providing a mathematical foundation for advanced computing concepts.""",
        },
    },
    "20CS3T03": {
        1: {
            "title": "Unit 1: Basic Structure of Computers",
            "content": """### UNIT 1: Basic Structure of Computers

#### Introduction

Computer organization deals with the internal structure and operation of computers. It focuses on how different components interact to execute programs.

This unit introduces the basic components of a computer system and their functions.

#### Detailed Explanation

**Functional Units**
A computer consists of input, output, memory, and processing units. Each unit performs a specific function.

For example, the CPU processes instructions, while memory stores data.

**Instruction Cycle**
The instruction cycle involves fetching, decoding, and executing instructions.

This cycle is repeated continuously during program execution.

#### Applications

Computer organization is essential for designing efficient hardware and understanding system performance.

#### Summary

This unit introduces the structure and operation of computer systems.""",
        },
        2: {
            "title": "Unit 2: Arithmetic and Logic Unit",
            "content": """### UNIT 2: Arithmetic and Logic Unit

#### Introduction

The Arithmetic and Logic Unit (ALU) performs arithmetic and logical operations in a computer.

This unit focuses on its design and operations.

#### Detailed Explanation

**Arithmetic Operations**
The ALU performs operations such as addition, subtraction, multiplication, and division.

These operations are fundamental for computations.

**Logical Operations**
Logical operations include AND, OR, and NOT, which are used in decision making.

#### Applications

The ALU is used in processors, calculators, and embedded systems.

#### Summary

This unit explains the role of the ALU in performing computations.""",
        },
        3: {
            "title": "Unit 3: Memory Organization",
            "content": """### UNIT 3: Memory Organization

#### Introduction

Memory organization refers to the structure and operation of memory systems in a computer.

This unit focuses on types of memory and their hierarchy.

#### Detailed Explanation

**Memory Hierarchy**
Memory is organized in levels such as registers, cache, main memory, and secondary storage.

Each level has different speed and capacity.

**Cache Memory**
Cache improves performance by storing frequently used data.

It reduces access time.

#### Applications

Memory organization is crucial for system performance and efficiency.

#### Summary

This unit introduces memory systems and their importance.""",
        },
        4: {
            "title": "Unit 4: Input/Output Organization",
            "content": """### UNIT 4: Input/Output Organization

#### Introduction

Input/output organization deals with communication between the computer and external devices.

This unit focuses on I/O devices and techniques.

#### Detailed Explanation

**I/O Devices**
Devices such as keyboards, monitors, and printers are used for input and output operations.

**I/O Techniques**
Techniques such as programmed I/O and interrupt-driven I/O improve efficiency.

#### Applications

I/O organization is essential for system interaction and data transfer.

#### Summary

This unit explains input/output mechanisms in computer systems.""",
        },
        5: {
            "title": "Unit 5: Control Unit",
            "content": """### UNIT 5: Control Unit

#### Introduction

The control unit manages the execution of instructions in a computer.

It directs operations of all components.

#### Detailed Explanation

**Functions of Control Unit**
It generates control signals and coordinates activities of the CPU.

**Types of Control Units**
Hardwired and microprogrammed control units differ in implementation.

#### Applications

Control units are essential in processors and embedded systems.

#### Summary

This unit introduces the control unit and its role in system operation.""",
        },
    },
    "20CS3T04": {
        1: {
            "title": "Unit 1: Introduction to DBMS",
            "content": """### UNIT 1: Introduction to DBMS

#### Introduction

A Database Management System (DBMS) is software that manages databases and provides mechanisms for storing, retrieving, and managing data.

This unit introduces DBMS concepts and architecture.

#### Detailed Explanation

**Database Concepts**
A database is a collection of related data. DBMS ensures data integrity and security.

**Advantages of DBMS**
It reduces redundancy and improves data consistency.

#### Applications

DBMS is used in banking, education, and e-commerce systems.

#### Summary

This unit introduces database systems and their importance.""",
        },
        2: {
            "title": "Unit 2: Relational Model",
            "content": """### UNIT 2: Relational Model

#### Introduction

The relational model organizes data into tables with rows and columns.

This unit focuses on relational databases.

#### Detailed Explanation

**Tables and Keys**
Tables consist of rows and columns, with primary keys uniquely identifying records.

**Relationships**
Relationships define how tables are connected.

#### Applications

Relational databases are widely used in modern applications.

#### Summary

This unit explains relational data organization.""",
        },
        3: {
            "title": "Unit 3: SQL and Database Design",
            "content": """### UNIT 3: SQL and Database Design

#### Introduction

SQL is used to interact with databases. Database design ensures efficient data storage.

#### Detailed Explanation

**SQL Commands**
Commands such as SELECT, INSERT, UPDATE, and DELETE are used.

**Normalization**
Normalization reduces redundancy and improves consistency.

#### Applications

SQL is used in data management and application development.

#### Summary

This unit covers SQL and design techniques.""",
        },
        4: {
            "title": "Unit 4: Transaction Management",
            "content": """### UNIT 4: Transaction Management

#### Introduction

Transactions ensure reliable database operations.

#### Detailed Explanation

**ACID Properties**
Transactions follow Atomicity, Consistency, Isolation, and Durability.

**Concurrency Control**
Ensures multiple transactions execute safely.

#### Applications

Transaction management is used in banking systems.

#### Summary

This unit explains reliable data operations.""",
        },
        5: {
            "title": "Unit 5: Indexing and Query Processing",
            "content": """### UNIT 5: Indexing and Query Processing

#### Introduction

Indexing improves database performance, and query processing retrieves data efficiently.

#### Detailed Explanation

**Indexing Techniques**
Indexes speed up data retrieval.

**Query Processing**
DBMS optimizes queries for efficient execution.

#### Applications

Used in search engines and large databases.

#### Summary

This unit introduces indexing and query optimization.""",
        },
    },
}


def upsert_subject(subject_code, units):
    subject = Subject.objects.get(subject_code=subject_code, is_active=True)
    unit_created = unit_updated = lesson_created = lesson_updated = 0

    for unit_number in sorted(units.keys()):
        data = units[unit_number]

        unit, unit_was_created = Unit.objects.get_or_create(
            subject=subject,
            unit_number=unit_number,
            defaults={
                "title": data["title"],
                "content": data["content"],
                "is_active": True,
            },
        )
        if unit_was_created:
            unit_created += 1
        else:
            changed = False
            if unit.title != data["title"]:
                unit.title = data["title"]
                changed = True
            if unit.content != data["content"]:
                unit.content = data["content"]
                changed = True
            if not unit.is_active:
                unit.is_active = True
                changed = True
            if changed:
                unit.save(update_fields=["title", "content", "is_active"])
                unit_updated += 1

        lesson, lesson_was_created = Lesson.objects.get_or_create(
            subject=subject,
            order=unit_number,
            defaults={
                "unit": unit,
                "title": data["title"],
                "content": data["content"],
                "is_active": True,
            },
        )
        if lesson_was_created:
            lesson_created += 1
        else:
            changed = False
            if lesson.unit_id != unit.id:
                lesson.unit = unit
                changed = True
            if lesson.title != data["title"]:
                lesson.title = data["title"]
                changed = True
            if lesson.content != data["content"]:
                lesson.content = data["content"]
                changed = True
            if not lesson.is_active:
                lesson.is_active = True
                changed = True
            if changed:
                lesson.save(update_fields=["unit", "title", "content", "is_active"])
                lesson_updated += 1

    return {
        "subject_code": subject_code,
        "units_created": unit_created,
        "units_updated": unit_updated,
        "lessons_created": lesson_created,
        "lessons_updated": lesson_updated,
        "total_active_lessons_for_subject": Lesson.objects.filter(subject=subject, is_active=True).count(),
    }


def main():
    results = [upsert_subject(code, units) for code, units in DATA.items()]
    print({"results": results})


if __name__ == "__main__":
    main()
