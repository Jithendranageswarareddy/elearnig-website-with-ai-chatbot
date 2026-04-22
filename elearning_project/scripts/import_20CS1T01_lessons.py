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


SUBJECT_CODE = "20CS1T01"

UNIT_CONTENT = {
    1: {
        "title": "Unit 1: Introduction to Programming and Problem Solving",
        "content": """### UNIT 1: Introduction to Programming and Problem Solving

#### Introduction

Programming is the process of designing and building a set of instructions that enable a computer to perform specific tasks. In the context of problem solving, programming serves as a bridge between human logic and machine execution. This unit introduces students to the fundamental concepts of problem solving and how these concepts are translated into executable programs. It emphasizes the importance of logical thinking, algorithm design, and structured approaches to solving computational problems.

The ability to break down complex problems into smaller, manageable components is a key skill in computer science. This unit also highlights the role of algorithms and flowcharts in representing solutions clearly before implementing them in a programming language.

#### Detailed Explanation

**Problem Solving Techniques**
Problem solving in programming involves identifying the problem, analyzing it, and developing a logical sequence of steps to arrive at a solution. Techniques such as decomposition, pattern recognition, abstraction, and algorithm design are essential. Decomposition involves breaking a problem into smaller parts, making it easier to handle. Pattern recognition helps identify similarities with previously solved problems, while abstraction focuses on ignoring unnecessary details and concentrating on relevant aspects.

For example, solving a problem like calculating the average of a list of numbers involves breaking it into steps such as reading input, summing numbers, and dividing by count. These steps can then be translated into a program.

**Algorithms and Flowcharts**
An algorithm is a finite sequence of well-defined steps used to solve a problem. It must be clear, precise, and unambiguous. Flowcharts provide a graphical representation of algorithms using symbols like rectangles for processes and diamonds for decisions.

For instance, an algorithm to check whether a number is even or odd includes steps like reading the number, dividing it by 2, and checking the remainder. The corresponding flowchart visually represents these steps, making it easier to understand the logic.

**Programming Languages and Translators**
Programming languages are formal languages used to communicate instructions to a computer. They can be classified into low-level languages (machine language and assembly language) and high-level languages (such as C, Python, and Java). Translators like compilers and interpreters convert high-level code into machine-readable form.

A compiler translates the entire program at once, while an interpreter executes code line by line. Understanding these concepts helps students grasp how programs are executed internally.

#### Applications

The concepts introduced in this unit are applied in software development, system design, and automation. Problem-solving techniques are used in developing applications ranging from simple calculators to complex systems like banking software. Algorithms and flowcharts are widely used in designing efficient solutions before implementation, ensuring correctness and clarity.

#### Summary

This unit establishes the foundation for programming by introducing problem-solving techniques, algorithms, and programming languages. It emphasizes logical thinking and structured approaches, which are essential for writing effective programs.""",
    },
    2: {
        "title": "Unit 2: C Programming Basics",
        "content": """### UNIT 2: C Programming Basics

#### Introduction

C is a powerful, general-purpose programming language widely used for system programming and application development. This unit introduces the basic syntax and structure of C programs, providing a foundation for writing simple programs. It focuses on understanding variables, data types, operators, and input/output operations.

Learning C helps students develop a strong understanding of how programs interact with memory and hardware, making it an ideal language for beginners in computer science.

#### Detailed Explanation

**Structure of a C Program**
A C program typically consists of preprocessor directives, a main function, variable declarations, and executable statements. The `main()` function is the entry point of any C program.

For example, a simple program to print \"Hello World\" includes the `#include<stdio.h>` directive, the `main()` function, and the `printf()` statement. Understanding this structure is essential for writing and debugging programs.

**Variables and Data Types**
Variables are used to store data, and each variable has a specific data type such as `int`, `float`, `char`, or `double`. Data types define the type of data a variable can hold and the operations that can be performed on it.

For instance, an integer variable can store whole numbers, while a float variable stores decimal values. Proper use of data types ensures efficient memory usage and accurate computations.

**Operators and Expressions**
Operators perform operations on variables and values. Common types include arithmetic operators (`+`, `-`, `*`, `/`), relational operators (`<`, `>`, `==`), and logical operators (`&&`, `||`). Expressions are combinations of variables, constants, and operators.

For example, the expression `a + b * c` follows operator precedence rules, where multiplication is performed before addition.

**Input and Output Functions**
C provides functions like `scanf()` and `printf()` for input and output operations. These functions allow users to interact with programs by entering data and displaying results.

For example, a program that reads two numbers and prints their sum uses `scanf()` to take input and `printf()` to display the result.

#### Applications

C programming is widely used in system programming, embedded systems, and operating system development. It is also used in developing compilers, interpreters, and database systems due to its efficiency and control over hardware.

#### Summary

This unit introduces the basic elements of C programming, including program structure, variables, data types, operators, and input/output operations. These concepts form the building blocks for writing more complex programs.""",
    },
    3: {
        "title": "Unit 3: Control Structures",
        "content": """### UNIT 3: Control Structures

#### Introduction

Control structures determine the flow of execution in a program. They allow programs to make decisions, repeat tasks, and execute statements conditionally. This unit focuses on different types of control structures in C, such as selection and iteration statements.

Understanding control structures is essential for writing dynamic and flexible programs that can handle different scenarios.

#### Detailed Explanation

**Conditional Statements**
Conditional statements allow a program to execute certain blocks of code based on specific conditions. The `if`, `if-else`, and `switch` statements are commonly used.

For example, an `if-else` statement can be used to check whether a number is positive or negative. The `switch` statement is useful when multiple conditions need to be evaluated based on a single variable.

**Looping Constructs**
Loops are used to execute a block of code repeatedly. Common loops in C include `for`, `while`, and `do-while`. Each loop has its own structure and use cases.

For instance, a `for` loop is ideal when the number of iterations is known, while a `while` loop is used when the condition is checked before execution.

**Nested Control Structures**
Control structures can be nested within each other to solve complex problems. For example, a loop can contain an `if` statement to perform conditional operations during each iteration.

#### Applications

Control structures are used in almost every program, from simple calculations to complex algorithms. They are essential in applications like data processing, game development, and real-time systems where decision-making and repetition are required.

#### Summary

This unit covers conditional and looping constructs that control program execution. Mastery of these structures enables the development of efficient and dynamic programs.""",
    },
    4: {
        "title": "Unit 4: Functions and Arrays",
        "content": """### UNIT 4: Functions and Arrays

#### Introduction

Functions and arrays are fundamental concepts in C programming that promote modularity and efficient data handling. Functions allow code reuse, while arrays enable the storage of multiple values in a single variable.

This unit focuses on defining and using functions, passing arguments, and working with arrays.

#### Detailed Explanation

**Functions**
Functions are blocks of code designed to perform specific tasks. They improve code readability and reusability. A function can take inputs (parameters) and return a value.

For example, a function to calculate the sum of two numbers can be defined and called multiple times within a program, reducing redundancy.

**Parameter Passing**
Parameters can be passed to functions either by value or by reference. In pass-by-value, a copy of the variable is passed, while in pass-by-reference, the actual variable is passed using pointers.

This distinction is important for understanding how changes in functions affect variables.

**Arrays**
An array is a collection of elements of the same data type stored in contiguous memory locations. Arrays can be one-dimensional or multi-dimensional.

For example, an array of integers can store marks of students, and a two-dimensional array can represent a matrix.

#### Applications

Functions are widely used in modular programming and large-scale software development. Arrays are used in data storage, sorting algorithms, and matrix operations, making them essential in scientific and engineering applications.

#### Summary

This unit introduces functions and arrays, emphasizing modular programming and efficient data handling. These concepts are crucial for building structured and scalable programs.""",
    },
    5: {
        "title": "Unit 5: Pointers and Structures",
        "content": """### UNIT 5: Pointers and Structures

#### Introduction

Pointers and structures are advanced features of C that provide powerful ways to manage memory and organize data. Pointers allow direct access to memory locations, while structures enable grouping of different data types.

This unit helps students understand memory management and data organization in C.

#### Detailed Explanation

**Pointers**
A pointer is a variable that stores the address of another variable. Pointers are used for dynamic memory allocation, passing arguments by reference, and efficient array handling.

For example, a pointer to an integer stores the address of that integer variable, allowing direct manipulation of its value.

**Pointer Arithmetic**
Pointer arithmetic allows operations like incrementing or decrementing pointers to access array elements efficiently. This is particularly useful when working with arrays and dynamic memory.

**Structures**
Structures are user-defined data types that group variables of different types under a single name. They are used to represent complex data like student records or employee details.

For example, a structure can store a student's name, roll number, and marks in a single entity.

#### Applications

Pointers are extensively used in system programming, dynamic memory allocation, and data structures like linked lists. Structures are used in database management, file handling, and real-world data modeling.

#### Summary

This unit covers pointers and structures, which are essential for advanced programming in C. These concepts enable efficient memory usage and organized data representation, forming the basis for complex applications.""",
    },
}


def main():
    subject = Subject.objects.get(subject_code=SUBJECT_CODE, is_active=True)

    unit_created = 0
    unit_updated = 0
    lesson_created = 0
    lesson_updated = 0

    for unit_number in sorted(UNIT_CONTENT.keys()):
        data = UNIT_CONTENT[unit_number]
        unit, created = Unit.objects.get_or_create(
            subject=subject,
            unit_number=unit_number,
            defaults={
                "title": data["title"],
                "content": data["content"],
                "is_active": True,
            },
        )
        if created:
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

        lesson_title = data["title"]
        lesson, l_created = Lesson.objects.get_or_create(
            subject=subject,
            order=unit_number,
            defaults={
                "unit": unit,
                "title": lesson_title,
                "content": data["content"],
                "is_active": True,
            },
        )
        if l_created:
            lesson_created += 1
        else:
            changed = False
            if lesson.unit_id != unit.id:
                lesson.unit = unit
                changed = True
            if lesson.title != lesson_title:
                lesson.title = lesson_title
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

    total_lessons = Lesson.objects.filter(subject=subject, is_active=True).count()

    print(
        {
            "subject_code": SUBJECT_CODE,
            "units_created": unit_created,
            "units_updated": unit_updated,
            "lessons_created": lesson_created,
            "lessons_updated": lesson_updated,
            "total_active_lessons_for_subject": total_lessons,
        }
    )


if __name__ == "__main__":
    main()
