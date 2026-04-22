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
    "20CS4T01": {
        1: {
            "title": "Unit 1: OS Fundamentals",
            "content": '''### UNIT 1: OS Fundamentals

#### Introduction

An Operating System (OS) is system software that acts as an interface between the user and computer hardware. It manages hardware resources and provides services for application programs. This unit introduces the fundamental concepts of operating systems, their functions, and types.

Operating systems play a crucial role in ensuring efficient execution of programs, resource allocation, and system security. Understanding OS fundamentals is essential for building and managing modern computing systems.

#### Detailed Explanation

**Functions of Operating Systems**
An OS performs various functions such as process management, memory management, file handling, and device management. It ensures that resources are allocated efficiently and that multiple programs can run simultaneously.

For example, the OS schedules processes to ensure fair CPU usage.

**Types of Operating Systems**
Operating systems can be classified into batch systems, time-sharing systems, distributed systems, and real-time systems. Each type is designed for specific applications and requirements.

Time-sharing systems allow multiple users to interact with the system simultaneously.

**System Calls and Services**
System calls provide an interface for programs to interact with the OS. They enable operations such as file access, process control, and communication.

#### Applications

Operating systems are used in computers, smartphones, servers, and embedded systems. They are essential for running applications and managing hardware resources.

#### Summary

This unit introduces the basic concepts and functions of operating systems, providing a foundation for further study.''',
        },
        2: {
            "title": "Unit 2: Process Management",
            "content": '''### UNIT 2: Process Management

#### Introduction

Process management deals with the creation, scheduling, and termination of processes. A process is a program in execution, and managing processes efficiently is a key function of an OS.

This unit focuses on process concepts, scheduling, and synchronization.

#### Detailed Explanation

**Process Concepts**
A process includes code, data, and system resources. Each process has a unique identifier and states such as ready, running, and waiting.

The process control block (PCB) stores information about each process.

**CPU Scheduling**
Scheduling algorithms determine which process gets CPU time. Common algorithms include First Come First Serve (FCFS), Shortest Job First (SJF), and Round Robin.

Efficient scheduling improves system performance.

**Process Synchronization**
Synchronization ensures that processes do not interfere with each other when accessing shared resources.

Mechanisms such as semaphores and mutexes are used.

#### Applications

Process management is used in multitasking systems, real-time systems, and distributed computing.

#### Summary

This unit covers process creation, scheduling, and synchronization, which are essential for multitasking systems.''',
        },
        3: {
            "title": "Unit 3: Memory Management",
            "content": '''### UNIT 3: Memory Management

#### Introduction

Memory management involves managing primary memory to ensure efficient allocation and usage. It is a critical function of an OS.

This unit focuses on memory allocation techniques and virtual memory.

#### Detailed Explanation

**Memory Allocation Techniques**
Techniques such as contiguous allocation and paging are used to manage memory.

Paging divides memory into fixed-size blocks.

**Virtual Memory**
Virtual memory allows programs to use more memory than physically available by using disk storage.

This improves system efficiency.

**Segmentation**
Segmentation divides memory into logical segments based on program structure.

#### Applications

Memory management is used in modern operating systems to support multitasking and efficient resource utilization.

#### Summary

This unit introduces memory management techniques and virtual memory concepts.''',
        },
        4: {
            "title": "Unit 4: File Systems",
            "content": '''### UNIT 4: File Systems

#### Introduction

File systems manage data storage on secondary storage devices. They provide a way to organize, store, and retrieve data efficiently.

This unit focuses on file organization and management techniques.

#### Detailed Explanation

**File Concepts**
A file is a collection of related data stored on storage devices.

File attributes include name, size, and permissions.

**Directory Structure**
Directories organize files into hierarchical structures.

This improves data management.

**File Allocation Methods**
Methods such as contiguous, linked, and indexed allocation are used.

#### Applications

File systems are used in operating systems, databases, and storage devices.

#### Summary

This unit covers file organization and management in operating systems.''',
        },
        5: {
            "title": "Unit 5: Deadlocks and Security",
            "content": '''### UNIT 5: Deadlocks and Security

#### Introduction

Deadlocks occur when processes are unable to proceed due to resource conflicts. Security ensures protection of system resources and data.

This unit focuses on deadlock handling and system security.

#### Detailed Explanation

**Deadlock Conditions**
Deadlocks occur due to mutual exclusion, hold and wait, no preemption, and circular wait.

**Deadlock Prevention and Avoidance**
Techniques such as resource allocation graphs and Banker’s algorithm are used.

**Security Mechanisms**
Security includes authentication, authorization, and encryption.

#### Applications

Deadlock handling and security are essential in operating systems and distributed systems.

#### Summary

This unit introduces deadlocks and security concepts for safe system operation.''',
        },
    },
    "20CS4T02": {
        1: {
            "title": "Unit 1: Algorithm Analysis",
            "content": '''### UNIT 1: Algorithm Analysis

#### Introduction

Algorithm analysis evaluates the efficiency of algorithms in terms of time and space complexity. It helps in selecting the best algorithm for a given problem.

This unit introduces asymptotic analysis and complexity measures.

#### Detailed Explanation

**Time Complexity**
Time complexity measures the execution time of an algorithm.

Big O notation is used to express complexity.

**Space Complexity**
Space complexity measures memory usage.

**Asymptotic Notations**
Notations such as Big O, Omega, and Theta describe algorithm performance.

#### Applications

Algorithm analysis is used in optimizing software and solving computational problems efficiently.

#### Summary

This unit introduces complexity analysis and performance evaluation.''',
        },
        2: {
            "title": "Unit 2: Divide and Conquer",
            "content": '''### UNIT 2: Divide and Conquer

#### Introduction

Divide and conquer is a strategy that breaks a problem into smaller subproblems, solves them, and combines results.

This unit focuses on its applications.

#### Detailed Explanation

**Concept and Approach**
Problems are divided recursively into smaller parts.

**Examples**
Algorithms such as merge sort and quick sort use this technique.

#### Applications

Used in sorting, searching, and computational geometry.

#### Summary

This unit explains divide and conquer strategy.''',
        },
        3: {
            "title": "Unit 3: Greedy Algorithms",
            "content": '''### UNIT 3: Greedy Algorithms

#### Introduction

Greedy algorithms make locally optimal choices to achieve a global optimum.

#### Detailed Explanation

**Concept**
At each step, the best immediate choice is made.

**Examples**
Algorithms like Kruskal’s and Prim’s are based on greedy approach.

#### Applications

Used in optimization problems.

#### Summary

This unit introduces greedy methods.''',
        },
        4: {
            "title": "Unit 4: Dynamic Programming",
            "content": '''### UNIT 4: Dynamic Programming

#### Introduction

Dynamic programming solves problems by breaking them into overlapping subproblems.

#### Detailed Explanation

**Concept**
Stores results of subproblems to avoid recomputation.

**Examples**
Fibonacci sequence and knapsack problem.

#### Applications

Used in optimization and decision-making problems.

#### Summary

This unit explains dynamic programming techniques.''',
        },
        5: {
            "title": "Unit 5: NP-Complete Problems",
            "content": '''### UNIT 5: NP-Complete Problems

#### Introduction

NP-complete problems are complex problems for which no efficient solution is known.

#### Detailed Explanation

**Classes of Problems**
P, NP, and NP-complete classes.

**Examples**
Travelling Salesman Problem.

#### Applications

Used in theoretical computer science.

#### Summary

This unit introduces complexity classes.''',
        },
    },
    "20CS4T03": {
        1: {
            "title": "Unit 1: Software Development Life Cycle",
            "content": '''### UNIT 1: Software Development Life Cycle

#### Introduction

SDLC defines stages in software development.

#### Detailed Explanation

**Phases**
Planning, design, implementation, testing, and maintenance.

#### Applications

Used in project development.

#### Summary

This unit introduces SDLC.''',
        },
        2: {
            "title": "Unit 2: Requirements Engineering",
            "content": '''### UNIT 2: Requirements Engineering

#### Introduction

Focuses on gathering and analyzing requirements.

#### Detailed Explanation

**Requirement Types**
Functional and non-functional.

#### Applications

Used in system design.

#### Summary

This unit explains requirements.''',
        },
        3: {
            "title": "Unit 3: Design Concepts",
            "content": '''### UNIT 3: Design Concepts

#### Introduction

Design defines system architecture.

#### Detailed Explanation

**Principles**
Modularity and abstraction.

#### Applications

Used in software development.

#### Summary

This unit introduces design concepts.''',
        },
        4: {
            "title": "Unit 4: Testing Strategies",
            "content": '''### UNIT 4: Testing Strategies

#### Introduction

Testing ensures software quality.

#### Detailed Explanation

**Types**
Unit, integration, and system testing.

#### Applications

Used in quality assurance.

#### Summary

This unit explains testing.''',
        },
        5: {
            "title": "Unit 5: Maintenance and Project Management",
            "content": '''### UNIT 5: Maintenance and Project Management

#### Introduction

Maintenance ensures software longevity.

#### Detailed Explanation

**Types of Maintenance**
Corrective, adaptive, and perfective.

#### Applications

Used in project management.

#### Summary

This unit explains maintenance.''',
        },
    },
    "20CS4T04": {
        1: {
            "title": "Unit 1: Network Fundamentals",
            "content": '''### UNIT 1: Network Fundamentals

#### Introduction

Computer networks connect devices for communication.

#### Detailed Explanation

**Types of Networks**
LAN, WAN, and MAN.

#### Applications

Used in communication systems.

#### Summary

This unit introduces networking basics.''',
        },
        2: {
            "title": "Unit 2: Data Link Layer",
            "content": '''### UNIT 2: Data Link Layer

#### Introduction

Ensures reliable data transfer.

#### Detailed Explanation

**Functions**
Error detection and correction.

#### Applications

Used in communication protocols.

#### Summary

This unit explains data link layer.''',
        },
        3: {
            "title": "Unit 3: Network Layer",
            "content": '''### UNIT 3: Network Layer

#### Introduction

Handles routing and addressing.

#### Detailed Explanation

**Protocols**
IP protocol.

#### Applications

Used in internet communication.

#### Summary

This unit explains network layer.''',
        },
        4: {
            "title": "Unit 4: Transport Layer",
            "content": '''### UNIT 4: Transport Layer

#### Introduction

Ensures end-to-end communication.

#### Detailed Explanation

**Protocols**
TCP and UDP.

#### Applications

Used in reliable communication.

#### Summary

This unit explains transport layer.''',
        },
        5: {
            "title": "Unit 5: Application Layer",
            "content": '''### UNIT 5: Application Layer

#### Introduction

Provides user-level services.

#### Detailed Explanation

**Protocols**
HTTP, FTP, SMTP.

#### Applications

Used in web and email services.

#### Summary

This unit explains application layer.''',
        },
    },
    "20CS5T01": {
        1: {
            "title": "Unit 1: Introduction to AI",
            "content": '''### UNIT 1: Introduction to AI

#### Introduction

Artificial Intelligence (AI) is a branch of computer science that focuses on creating systems capable of performing tasks that typically require human intelligence. These tasks include reasoning, learning, problem solving, perception, and language understanding. AI aims to simulate human cognitive processes and enhance decision-making capabilities in machines.

The evolution of AI has led to significant advancements in various fields such as healthcare, robotics, natural language processing, and autonomous systems. This unit introduces the fundamental concepts, history, and scope of AI, providing a strong foundation for understanding intelligent systems.

#### Detailed Explanation

**Definition and Scope of AI**
AI can be defined as the ability of a machine to mimic intelligent human behavior. It encompasses areas such as machine learning, natural language processing, robotics, and computer vision. AI systems can be categorized as narrow AI, which is designed for specific tasks, and general AI, which aims to perform any intellectual task that a human can do.

For example, virtual assistants like chatbots represent narrow AI, while general AI remains largely theoretical.

**History and Evolution of AI**
AI has evolved through several phases, starting from early symbolic reasoning systems to modern data-driven approaches. The development of machine learning and deep learning has significantly improved AI capabilities.

Early AI systems relied heavily on rule-based approaches, while modern systems use large datasets and algorithms to learn patterns.

**Applications of AI**
AI is widely used in various domains such as healthcare for disease diagnosis, finance for fraud detection, and transportation for autonomous vehicles.

These applications demonstrate the transformative potential of AI in solving complex real-world problems.

#### Applications

AI is applied in recommendation systems, robotics, speech recognition, and intelligent automation. It enhances efficiency and decision-making across industries.

#### Summary

This unit introduces the concept, history, and applications of AI, highlighting its importance in modern technology.''',
        },
        2: {
            "title": "Unit 2: Search Techniques",
            "content": '''### UNIT 2: Search Techniques

#### Introduction

Search techniques are fundamental to AI as they enable problem-solving by exploring possible solutions. These techniques help in navigating through large solution spaces efficiently.

This unit focuses on different search strategies used in AI.

#### Detailed Explanation

**Uninformed Search Techniques**
Uninformed or blind search methods do not use additional knowledge about the problem. Examples include Breadth First Search (BFS) and Depth First Search (DFS).

BFS explores all nodes at the present level before moving to the next level, while DFS explores as far as possible along a branch.

**Informed Search Techniques**
Informed search techniques use heuristics to guide the search process. A* algorithm is a popular example that uses cost functions to find optimal solutions.

Heuristics improve efficiency by reducing the search space.

**Heuristic Functions**
A heuristic function estimates the cost to reach the goal from a given node.

For example, in pathfinding, the straight-line distance can be used as a heuristic.

#### Applications

Search techniques are used in game playing, robotics navigation, and route optimization.

#### Summary

This unit explains search strategies and their role in problem solving in AI.''',
        },
        3: {
            "title": "Unit 3: Knowledge Representation",
            "content": '''### UNIT 3: Knowledge Representation

#### Introduction

Knowledge representation is a key aspect of AI that involves structuring information so that machines can understand and reason about it.

This unit focuses on different methods of representing knowledge.

#### Detailed Explanation

**Types of Knowledge Representation**
Knowledge can be represented using logical representations, semantic networks, frames, and production rules.

Each method provides a way to organize and process information.

**Logic-Based Representation**
Propositional and predicate logic are used to represent facts and relationships.

These representations allow reasoning through inference mechanisms.

**Semantic Networks and Frames**
Semantic networks represent knowledge as graphs, while frames represent structured data.

These methods are useful for representing complex relationships.

#### Applications

Knowledge representation is used in expert systems, natural language processing, and intelligent agents.

#### Summary

This unit introduces various methods for representing knowledge in AI systems.''',
        },
        4: {
            "title": "Unit 4: Machine Learning Basics",
            "content": '''### UNIT 4: Machine Learning Basics

#### Introduction

Machine learning is a subset of AI that enables systems to learn from data and improve performance over time.

This unit introduces the basic concepts of machine learning.

#### Detailed Explanation

**Types of Machine Learning**
Machine learning can be supervised, unsupervised, or reinforcement learning.

Supervised learning uses labeled data, while unsupervised learning identifies patterns in unlabeled data.

**Common Algorithms**
Algorithms such as linear regression, decision trees, and clustering techniques are widely used.

These algorithms help in prediction and classification tasks.

**Model Evaluation**
Performance metrics such as accuracy, precision, and recall are used to evaluate models.

#### Applications

Machine learning is used in recommendation systems, fraud detection, and image recognition.

#### Summary

This unit introduces machine learning concepts and algorithms.''',
        },
        5: {
            "title": "Unit 5: Expert Systems",
            "content": '''### UNIT 5: Expert Systems

#### Introduction

Expert systems are AI programs that simulate the decision-making ability of human experts.

This unit focuses on their structure and applications.

#### Detailed Explanation

**Components of Expert Systems**
An expert system consists of a knowledge base and an inference engine.

The knowledge base stores information, while the inference engine applies rules.

**Working of Expert Systems**
They use rules and logic to provide solutions or recommendations.

For example, medical diagnosis systems assist doctors.

#### Applications

Expert systems are used in healthcare, finance, and technical support.

#### Summary

This unit explains expert systems and their role in decision-making.''',
        },
    },
    "20CS5T02": {
        1: {
            "title": "Unit 1: Introduction to Compilers",
            "content": '''### UNIT 1: Introduction to Compilers

#### Introduction

A compiler is a software tool that translates high-level programming language code into machine code. It plays a crucial role in program execution.

This unit introduces compiler structure and phases.

#### Detailed Explanation

**Phases of Compiler**
The main phases include lexical analysis, syntax analysis, semantic analysis, optimization, and code generation.

Each phase transforms the program step by step.

**Compiler vs Interpreter**
A compiler translates the entire program at once, while an interpreter executes line by line.

#### Applications

Compilers are used in programming languages and software development.

#### Summary

This unit introduces compiler fundamentals.''',
        },
        2: {
            "title": "Unit 2: Lexical Analysis",
            "content": '''### UNIT 2: Lexical Analysis

#### Introduction

Lexical analysis is the first phase of a compiler.

#### Detailed Explanation

**Tokens and Lexemes**
Tokens represent basic units of code, while lexemes are actual sequences.

**Role of Lexer**
It removes whitespace and identifies tokens.

#### Applications

Used in compilers and interpreters.

#### Summary

This unit explains lexical analysis.''',
        },
        3: {
            "title": "Unit 3: Syntax Analysis",
            "content": '''### UNIT 3: Syntax Analysis

#### Introduction

Syntax analysis checks the grammatical structure.

#### Detailed Explanation

**Parsing Techniques**
Top-down and bottom-up parsing.

**Parse Trees**
Represent program structure.

#### Applications

Used in compilers.

#### Summary

This unit explains syntax analysis.''',
        },
        4: {
            "title": "Unit 4: Semantic Analysis",
            "content": '''### UNIT 4: Semantic Analysis

#### Introduction

Ensures program meaning is correct.

#### Detailed Explanation

**Type Checking**
Ensures compatibility.

**Symbol Table**
Stores variable information.

#### Applications

Used in compilers.

#### Summary

This unit explains semantic analysis.''',
        },
        5: {
            "title": "Unit 5: Code Generation",
            "content": '''### UNIT 5: Code Generation

#### Introduction

Final phase generating machine code.

#### Detailed Explanation

**Intermediate Code**
Represents program.

**Optimization**
Improves efficiency.

#### Applications

Used in compilers.

#### Summary

This unit explains code generation.''',
        },
    },
    "20CS5T03": {
        1: {
            "title": "Unit 1: Data Warehousing Concepts",
            "content": '''### UNIT 1: Data Warehousing Concepts

#### Introduction

Data warehousing involves collecting and managing large volumes of data.

#### Detailed Explanation

**Characteristics**
Subject-oriented, integrated, time-variant.

**Architecture**
Includes ETL process.

#### Applications

Used in business intelligence.

#### Summary

This unit explains data warehousing.''',
        },
        2: {
            "title": "Unit 2: Data Preprocessing",
            "content": '''### UNIT 2: Data Preprocessing

#### Introduction

Prepares data for mining.

#### Detailed Explanation

**Data Cleaning**
Removes noise.

**Data Transformation**
Converts formats.

#### Applications

Used in analytics.

#### Summary

This unit explains preprocessing.''',
        },
        3: {
            "title": "Unit 3: Data Mining Techniques",
            "content": '''### UNIT 3: Data Mining Techniques

#### Introduction

Extracts patterns from data.

#### Detailed Explanation

**Classification and Clustering**
Identify patterns.

#### Applications

Used in analytics.

#### Summary

This unit explains mining.''',
        },
        4: {
            "title": "Unit 4: Association Rules",
            "content": '''### UNIT 4: Association Rules

#### Introduction

Finds relationships.

#### Detailed Explanation

**Apriori Algorithm**
Finds frequent itemsets.

#### Applications

Used in market analysis.

#### Summary

This unit explains association.''',
        },
        5: {
            "title": "Unit 5: Clustering and Classification",
            "content": '''### UNIT 5: Clustering and Classification

#### Introduction

Groups data.

#### Detailed Explanation

**Techniques**
K-means, decision trees.

#### Applications

Used in ML.

#### Summary

This unit explains clustering.''',
        },
    },
    "20CS5T04": {
        1: {
            "title": "Unit 1: Web Fundamentals",
            "content": '''### UNIT 1: Web Fundamentals

#### Introduction

Web technologies enable communication over the internet.

#### Detailed Explanation

**HTTP Protocol**
Used for communication.

**Web Architecture**
Client-server model.

#### Applications

Used in web development.

#### Summary

This unit explains fundamentals.''',
        },
        2: {
            "title": "Unit 2: HTML and CSS",
            "content": '''### UNIT 2: HTML and CSS

#### Introduction

HTML structures content, CSS styles it.

#### Detailed Explanation

**HTML Elements**
Tags define structure.

**CSS Styling**
Controls layout.

#### Applications

Used in websites.

#### Summary

This unit explains HTML and CSS.''',
        },
        3: {
            "title": "Unit 3: JavaScript",
            "content": '''### UNIT 3: JavaScript

#### Introduction

JavaScript adds interactivity.

#### Detailed Explanation

**DOM Manipulation**
Changes webpage.

**Event Handling**
Responds to actions.

#### Applications

Used in dynamic pages.

#### Summary

This unit explains JavaScript.''',
        },
        4: {
            "title": "Unit 4: Server-Side Technologies",
            "content": '''### UNIT 4: Server-Side Technologies

#### Introduction

Handles backend logic.

#### Detailed Explanation

**Languages**
PHP, Node.js.

**Database Interaction**
Connects to DB.

#### Applications

Used in web apps.

#### Summary

This unit explains server-side.''',
        },
        5: {
            "title": "Unit 5: Web Security",
            "content": '''### UNIT 5: Web Security

#### Introduction

Ensures safe web usage.

#### Detailed Explanation

**Threats**
XSS, SQL injection.

**Security Measures**
Encryption, authentication.

#### Applications

Used in secure systems.

#### Summary

This unit explains web security.''',
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
