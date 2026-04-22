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
    "20CS1T04": {
        1: {
            "title": "Unit 1: Mechanics",
            "content": """### UNIT 1: Mechanics

#### Introduction

Mechanics is one of the fundamental branches of physics that deals with the motion of objects and the forces acting upon them. It forms the basis for understanding physical phenomena in engineering and technology. This unit introduces the principles of motion, force, energy, and momentum, which are essential for analyzing mechanical systems.

The study of mechanics enables engineers to design machines, structures, and systems by understanding how objects behave under different forces. It provides a strong foundation for further topics in physics and engineering disciplines.

#### Detailed Explanation

**Kinematics**
Kinematics describes the motion of objects without considering the forces causing the motion. It involves parameters such as displacement, velocity, and acceleration.

For example, the motion of a car on a straight road can be described using equations of motion, which relate displacement, velocity, acceleration, and time.

**Newton’s Laws of Motion**
Newton’s laws form the foundation of classical mechanics. The first law states that an object remains at rest or in uniform motion unless acted upon by an external force. The second law relates force, mass, and acceleration, while the third law states that every action has an equal and opposite reaction.

These laws are widely used in analyzing mechanical systems and solving engineering problems.

**Work, Energy, and Power**
Work is done when a force causes displacement, and energy is the capacity to do work. Power is the rate at which work is done.

For example, kinetic energy depends on the velocity of an object, while potential energy depends on its position.

**Momentum and Collisions**
Momentum is the product of mass and velocity. The law of conservation of momentum states that the total momentum of a system remains constant in the absence of external forces.

This principle is applied in analyzing collisions and interactions between objects.

#### Applications

Mechanics is applied in mechanical engineering, robotics, aerospace engineering, and structural design. It is essential for designing vehicles, machines, and buildings.

#### Summary

This unit introduces the fundamental principles of motion, force, energy, and momentum. These concepts are essential for understanding and analyzing mechanical systems.""",
        },
        2: {
            "title": "Unit 2: Oscillations and Waves",
            "content": """### UNIT 2: Oscillations and Waves

#### Introduction

Oscillations and waves describe repetitive motion and energy transfer through space. These concepts are fundamental in understanding various physical systems such as sound, light, and mechanical vibrations.

This unit focuses on simple harmonic motion, wave properties, and their applications.

#### Detailed Explanation

**Simple Harmonic Motion (SHM)**
Simple harmonic motion is a type of periodic motion where the restoring force is proportional to displacement. Examples include the motion of a pendulum and a mass-spring system.

SHM is characterized by parameters such as amplitude, frequency, and time period.

**Wave Motion**
Waves transfer energy without transferring matter. They can be classified as mechanical waves and electromagnetic waves.

For example, sound waves require a medium to travel, while light waves can propagate in a vacuum.

**Properties of Waves**
Important properties of waves include wavelength, frequency, and velocity. The relationship between these quantities helps in understanding wave behavior.

Wave phenomena such as reflection, refraction, and interference are important in various applications.

#### Applications

Oscillations and waves are used in communication systems, acoustics, signal processing, and medical imaging technologies such as ultrasound.

#### Summary

This unit covers oscillatory motion and wave behavior, providing insights into energy transfer and periodic motion in physical systems.""",
        },
        3: {
            "title": "Unit 3: Optics",
            "content": """### UNIT 3: Optics

#### Introduction

Optics is the study of light and its interaction with matter. It plays a crucial role in various technological applications such as imaging, communication, and instrumentation.

This unit introduces the principles of reflection, refraction, and optical devices.

#### Detailed Explanation

**Reflection and Refraction**
Reflection occurs when light bounces off a surface, while refraction occurs when light changes direction as it passes through different media.

For example, a mirror reflects light, while a lens refracts light to form images.

**Interference and Diffraction**
Interference occurs when two waves combine to form a resultant wave, while diffraction involves the bending of light around obstacles.

These phenomena explain patterns such as fringes observed in experiments.

**Optical Instruments**
Devices such as microscopes, telescopes, and cameras use principles of optics to form images.

For example, a microscope magnifies small objects, while a telescope allows observation of distant objects.

#### Applications

Optics is used in fiber optic communication, medical imaging, photography, and laser technology. It is essential in modern communication systems.

#### Summary

This unit introduces the behavior of light and its applications in optical devices. It is fundamental for understanding imaging and communication technologies.""",
        },
        4: {
            "title": "Unit 4: Quantum Mechanics",
            "content": """### UNIT 4: Quantum Mechanics

#### Introduction

Quantum mechanics is a branch of physics that deals with the behavior of particles at atomic and subatomic levels. It provides a framework for understanding phenomena that cannot be explained by classical physics.

This unit introduces the basic concepts of quantum theory and their significance.

#### Detailed Explanation

**Wave-Particle Duality**
Particles such as electrons exhibit both wave-like and particle-like properties. This dual nature is a fundamental concept in quantum mechanics.

For example, electrons can produce interference patterns, demonstrating their wave nature.

**Heisenberg’s Uncertainty Principle**
This principle states that it is impossible to simultaneously determine the exact position and momentum of a particle.

This concept highlights the limitations of measurement at microscopic levels.

**Schrödinger Equation**
The Schrödinger equation describes the behavior of quantum systems and provides information about the probability of finding a particle in a given state.

It is a fundamental equation in quantum mechanics.

#### Applications

Quantum mechanics is used in semiconductor technology, quantum computing, lasers, and nanotechnology. It is essential for modern electronics and advanced research.

#### Summary

This unit introduces the principles of quantum mechanics, providing insights into the behavior of microscopic particles and their applications.""",
        },
        5: {
            "title": "Unit 5: Semiconductor Physics",
            "content": """### UNIT 5: Semiconductor Physics

#### Introduction

Semiconductor physics deals with the properties and behavior of semiconductor materials, which are essential for electronic devices.

This unit focuses on the structure, properties, and applications of semiconductors.

#### Detailed Explanation

**Semiconductor Materials**
Semiconductors have electrical conductivity between conductors and insulators. Common materials include silicon and germanium.

Their conductivity can be controlled by adding impurities, a process known as doping.

**PN Junction Diode**
A PN junction is formed by joining p-type and n-type semiconductors. It allows current to flow in one direction, making it useful in rectification.

For example, diodes are used in power supplies to convert AC to DC.

**Transistors**
Transistors are semiconductor devices used for amplification and switching. They are the building blocks of modern electronic circuits.

For example, transistors are used in computers, mobile devices, and communication systems.

#### Applications

Semiconductors are used in electronic devices such as computers, smartphones, solar cells, and integrated circuits. They form the foundation of modern electronics.

#### Summary

This unit covers semiconductor materials, PN junctions, and transistors. These concepts are essential for understanding electronic devices and systems.""",
        },
    },
    "20CS2T01": {
        1: {
            "title": "Unit 1: Introduction to Data Structures",
            "content": """### UNIT 1: Introduction to Data Structures

#### Introduction

Data structures are fundamental concepts in computer science that enable efficient storage, organization, and manipulation of data. They provide a systematic way of managing data so that it can be accessed and modified effectively. This unit introduces the concept of data structures, their importance, and classification.

In programming, choosing the right data structure is crucial for optimizing performance and resource utilization. This unit lays the foundation for understanding how different data structures are used to solve computational problems efficiently.

#### Detailed Explanation

**Definition and Importance of Data Structures**
A data structure is a way of organizing data in a computer so that it can be used efficiently. It determines how data is stored, accessed, and manipulated.

For example, storing student records in an array allows quick access using indices, while using a linked list provides flexibility in memory allocation.

**Types of Data Structures**
Data structures can be broadly classified into primitive and non-primitive types. Primitive data structures include basic data types such as integers and characters, while non-primitive structures include arrays, lists, stacks, and trees.

They can also be classified as linear and non-linear based on how elements are organized.

**Abstract Data Types (ADT)**
An Abstract Data Type defines a data structure in terms of its behavior rather than its implementation. It specifies operations that can be performed without defining how they are implemented.

For example, a stack ADT defines operations like push and pop without specifying the underlying structure.

#### Applications

Data structures are used in databases, operating systems, compilers, and artificial intelligence. They are essential for efficient data processing and algorithm design.

#### Summary

This unit introduces the concept, classification, and importance of data structures, providing a foundation for further study.""",
        },
        2: {
            "title": "Unit 2: Linear Data Structures",
            "content": """### UNIT 2: Linear Data Structures

#### Introduction

Linear data structures organize elements in a sequential manner where each element is connected to its predecessor and successor. These structures are simple and widely used in programming.

This unit focuses on arrays, linked lists, stacks, and queues, which are essential for understanding data organization.

#### Detailed Explanation

**Arrays**
An array is a collection of elements of the same type stored in contiguous memory locations. It allows direct access to elements using indices.

For example, an array can store marks of students, enabling quick retrieval of any element.

**Linked Lists**
A linked list consists of nodes where each node contains data and a reference to the next node. Unlike arrays, linked lists do not require contiguous memory.

This makes insertion and deletion operations more efficient.

**Stacks**
A stack follows the Last In First Out (LIFO) principle. Operations include push (insert) and pop (remove).

For example, stacks are used in function calls and expression evaluation.

**Queues**
A queue follows the First In First Out (FIFO) principle. Elements are inserted at the rear and removed from the front.

Queues are used in scheduling and buffering applications.

#### Applications

Linear data structures are used in memory management, scheduling algorithms, and expression evaluation. They form the basis for more complex data structures.

#### Summary

This unit covers arrays, linked lists, stacks, and queues, which are fundamental linear data structures used in programming.""",
        },
        3: {
            "title": "Unit 3: Non-Linear Data Structures",
            "content": """### UNIT 3: Non-Linear Data Structures

#### Introduction

Non-linear data structures organize data in a hierarchical or interconnected manner. Unlike linear structures, elements are not arranged sequentially.

This unit focuses on trees and graphs, which are widely used in complex applications.

#### Detailed Explanation

**Trees**
A tree is a hierarchical data structure consisting of nodes connected by edges. It has a root node and child nodes forming a parent-child relationship.

For example, a binary tree has at most two children for each node and is used in search operations.

**Binary Search Trees (BST)**
A BST is a type of binary tree where the left child contains smaller values and the right child contains larger values.

This property enables efficient searching, insertion, and deletion operations.

**Graphs**
A graph consists of vertices and edges representing relationships between entities. Graphs can be directed or undirected.

For example, social networks can be represented as graphs where users are nodes and connections are edges.

#### Applications

Non-linear data structures are used in databases, networking, artificial intelligence, and pathfinding algorithms. They are essential for representing complex relationships.

#### Summary

This unit introduces trees and graphs, highlighting their importance in representing hierarchical and networked data.""",
        },
        4: {
            "title": "Unit 4: Searching and Sorting",
            "content": """### UNIT 4: Searching and Sorting

#### Introduction

Searching and sorting are fundamental operations in data processing. Searching involves finding specific elements in a data set, while sorting arranges data in a particular order.

Efficient searching and sorting algorithms are essential for optimizing performance in applications.

#### Detailed Explanation

**Searching Techniques**
Searching methods include linear search and binary search. Linear search checks each element sequentially, while binary search divides the data set into halves for faster searching.

Binary search requires the data to be sorted and is more efficient than linear search.

**Sorting Algorithms**
Sorting algorithms include bubble sort, selection sort, insertion sort, merge sort, and quick sort. Each algorithm has different time complexities and use cases.

For example, merge sort is efficient for large data sets, while bubble sort is simple but less efficient.

**Time Complexity**
Time complexity measures the efficiency of algorithms in terms of execution time. It is expressed using Big O notation.

For example, linear search has O(n) complexity, while binary search has O(log n).

#### Applications

Searching and sorting are used in databases, search engines, and data analysis. They are essential for efficient data retrieval and organization.

#### Summary

This unit covers searching and sorting techniques, emphasizing algorithm efficiency and performance analysis.""",
        },
        5: {
            "title": "Unit 5: Advanced Data Structures",
            "content": """### UNIT 5: Advanced Data Structures

#### Introduction

Advanced data structures provide more efficient ways to store and manage data for complex applications. They are built upon basic data structures and are used in high-performance systems.

This unit introduces advanced structures such as heaps, hash tables, and balanced trees.

#### Detailed Explanation

**Heaps**
A heap is a complete binary tree used for priority queue operations. It can be a max-heap or min-heap based on the ordering of elements.

Heaps are commonly used in scheduling and graph algorithms.

**Hash Tables**
A hash table stores data using a hash function that maps keys to indices. This allows fast insertion, deletion, and lookup operations.

For example, hash tables are used in databases and caching systems.

**Balanced Trees**
Balanced trees such as AVL trees maintain height balance to ensure efficient operations.

These structures provide faster searching and insertion compared to unbalanced trees.

#### Applications

Advanced data structures are used in database indexing, memory management, networking, and artificial intelligence. They are essential for high-performance computing.

#### Summary

This unit introduces advanced data structures such as heaps, hash tables, and balanced trees. These structures enable efficient data handling in complex systems.""",
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
