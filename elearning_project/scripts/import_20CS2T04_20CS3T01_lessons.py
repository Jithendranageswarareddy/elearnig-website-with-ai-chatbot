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
    "20CS2T04": {
        1: {
            "title": "Unit 1: Ecosystems",
            "content": """### UNIT 1: Ecosystems

#### Introduction

An ecosystem is a functional unit of nature where living organisms interact with each other and with their physical environment. It includes biotic components such as plants, animals, and microorganisms, and abiotic components such as air, water, soil, and climate. This unit provides an understanding of ecosystem structure, functions, and energy flow, which are essential for maintaining ecological balance.

Ecosystems can vary in size and complexity, ranging from small ponds to large forests and oceans. Understanding ecosystems helps in analyzing environmental issues and developing sustainable solutions.

#### Detailed Explanation

**Structure of Ecosystems**
An ecosystem consists of producers, consumers, and decomposers. Producers, mainly green plants, convert solar energy into chemical energy through photosynthesis. Consumers depend on producers or other consumers for food, while decomposers break down organic matter and recycle nutrients.

For example, in a forest ecosystem, plants act as producers, herbivores like deer are primary consumers, and carnivores like tigers are secondary consumers.

**Energy Flow in Ecosystems**
Energy flows through an ecosystem in a unidirectional manner, starting from the sun to producers and then to consumers. This flow is represented using food chains and food webs.

Energy transfer between trophic levels is inefficient, with only a small percentage of energy being passed on, which explains the pyramid structure of ecosystems.

**Biogeochemical Cycles**
These cycles describe the movement of elements such as carbon, nitrogen, and water through the ecosystem.

For instance, the carbon cycle involves the exchange of carbon dioxide between the atmosphere, plants, and animals.

#### Applications

Understanding ecosystems helps in conservation planning, wildlife management, and environmental protection. It is also crucial in addressing climate change and maintaining biodiversity.

#### Summary

This unit explains ecosystem structure, energy flow, and nutrient cycles. These concepts are essential for understanding environmental interactions and sustainability.""",
        },
        2: {
            "title": "Unit 2: Natural Resources",
            "content": """### UNIT 2: Natural Resources

#### Introduction

Natural resources are materials and components that occur naturally in the environment and are used by humans for survival and development. These include water, soil, minerals, forests, and energy resources.

This unit focuses on the classification, utilization, and conservation of natural resources, highlighting their importance in sustainable development.

#### Detailed Explanation

**Types of Natural Resources**
Natural resources are classified as renewable and non-renewable. Renewable resources such as solar energy and wind can be replenished, while non-renewable resources like fossil fuels are limited.

Efficient utilization of these resources is essential to prevent depletion.

**Water Resources**
Water is a vital resource for life. Issues such as water scarcity, pollution, and overuse affect its availability. Conservation techniques such as rainwater harvesting help in sustainable management.

**Forest and Mineral Resources**
Forests provide ecological balance, biodiversity, and resources like timber. Mineral resources are essential for industrial development.

Overexploitation of these resources leads to environmental degradation.

#### Applications

Natural resource management is applied in agriculture, industry, and urban planning. Sustainable practices help in preserving resources for future generations.

#### Summary

This unit highlights the importance of natural resources and the need for their conservation and sustainable use.""",
        },
        3: {
            "title": "Unit 3: Biodiversity",
            "content": """### UNIT 3: Biodiversity

#### Introduction

Biodiversity refers to the variety of life forms on Earth, including plants, animals, and microorganisms. It plays a crucial role in maintaining ecological balance and supporting life systems.

This unit explores the types, importance, and conservation of biodiversity.

#### Detailed Explanation

**Types of Biodiversity**
Biodiversity can be classified into genetic diversity, species diversity, and ecosystem diversity. Each type contributes to the resilience and stability of ecosystems.

For example, genetic diversity within crops helps improve resistance to diseases.

**Importance of Biodiversity**
Biodiversity provides ecological, economic, and aesthetic benefits. It supports ecosystem services such as pollination, nutrient cycling, and climate regulation.

Loss of biodiversity can disrupt ecosystems and affect human life.

**Threats to Biodiversity**
Factors such as habitat destruction, pollution, and climate change threaten biodiversity. Conservation efforts are necessary to protect endangered species.

#### Applications

Biodiversity conservation is important in agriculture, medicine, and environmental management. It supports sustainable development and ecological balance.

#### Summary

This unit explains biodiversity and its importance, emphasizing the need for conservation and protection.""",
        },
        4: {
            "title": "Unit 4: Environmental Pollution",
            "content": """### UNIT 4: Environmental Pollution

#### Introduction

Environmental pollution refers to the introduction of harmful substances into the environment, causing adverse effects on living organisms and ecosystems.

This unit discusses different types of pollution, their causes, and control measures.

#### Detailed Explanation

**Types of Pollution**
Major types include air, water, soil, and noise pollution. Each type affects the environment differently.

For example, air pollution caused by vehicle emissions leads to respiratory problems.

**Causes and Effects**
Industrialization, urbanization, and improper waste disposal contribute to pollution.

Pollution affects human health, ecosystems, and climate patterns.

**Control Measures**
Pollution can be controlled through regulations, waste management, and adoption of clean technologies.

For instance, using renewable energy reduces air pollution.

#### Applications

Pollution control is essential in industries, urban planning, and environmental protection policies.

#### Summary

This unit covers types, causes, and control of environmental pollution, highlighting its impact on health and ecosystems.""",
        },
        5: {
            "title": "Unit 5: Sustainable Development",
            "content": """### UNIT 5: Sustainable Development

#### Introduction

Sustainable development aims to meet present needs without compromising the ability of future generations to meet their needs. It balances economic growth, environmental protection, and social well-being.

This unit focuses on principles and practices of sustainable development.

#### Detailed Explanation

**Principles of Sustainability**
Sustainability involves efficient resource use, environmental conservation, and social equity.

It encourages the use of renewable resources and reduction of waste.

**Sustainable Practices**
Practices such as recycling, energy conservation, and green technologies promote sustainability.

For example, solar energy reduces dependence on fossil fuels.

**Role of Individuals and Society**
Individuals and communities play a crucial role in achieving sustainability through responsible consumption and environmental awareness.

#### Applications

Sustainable development is applied in urban planning, agriculture, and industrial processes. It ensures long-term environmental and economic stability.

#### Summary

This unit emphasizes sustainable development and its importance in achieving environmental balance and economic growth.""",
        },
    },
    "20CS3T01": {
        1: {
            "title": "Unit 1: OOP Concepts",
            "content": """### UNIT 1: OOP Concepts

#### Introduction

Object Oriented Programming (OOP) is a programming paradigm that uses objects and classes to design software. It focuses on organizing code in a modular and reusable manner.

This unit introduces the basic concepts of OOP and their importance in software development.

#### Detailed Explanation

**Principles of OOP**
OOP is based on four main principles: encapsulation, abstraction, inheritance, and polymorphism. These principles help in designing efficient and maintainable programs.

Encapsulation hides data, abstraction simplifies complexity, inheritance enables reuse, and polymorphism allows flexibility.

**Advantages of OOP**
OOP improves code reusability, scalability, and maintainability. It allows developers to build complex systems using modular components.

#### Applications

OOP is widely used in software development, game development, and web applications. Languages like Java and C++ support OOP.

#### Summary

This unit introduces the core concepts of OOP, forming the foundation for object-oriented programming.""",
        },
        2: {
            "title": "Unit 2: Classes and Objects",
            "content": """### UNIT 2: Classes and Objects

#### Introduction

Classes and objects are the fundamental building blocks of OOP. A class defines a blueprint, while objects represent instances of that class.

This unit focuses on defining classes and creating objects.

#### Detailed Explanation

**Class Definition**
A class contains data members and member functions. It defines the structure and behavior of objects.

For example, a class \"Student\" may contain attributes like name and marks.

**Objects**
Objects are instances of classes that hold actual data. Multiple objects can be created from a single class.

**Constructors and Destructors**
Constructors initialize objects, while destructors clean up resources.

These functions are automatically invoked during object creation and destruction.

#### Applications

Classes and objects are used in designing real-world applications such as management systems and simulations.

#### Summary

This unit explains classes and objects, which are essential for implementing OOP concepts.""",
        },
        3: {
            "title": "Unit 3: Inheritance",
            "content": """### UNIT 3: Inheritance

#### Introduction

Inheritance allows one class to acquire properties and methods of another class. It promotes code reuse and hierarchical classification.

This unit focuses on types and applications of inheritance.

#### Detailed Explanation

**Types of Inheritance**
Common types include single, multiple, multilevel, and hierarchical inheritance.

Each type defines how classes are related and how properties are inherited.

**Benefits of Inheritance**
Inheritance reduces code duplication and enhances maintainability.

It allows the extension of existing classes.

#### Applications

Inheritance is used in software design patterns, frameworks, and application development.

#### Summary

This unit introduces inheritance and its role in code reuse and hierarchy.""",
        },
        4: {
            "title": "Unit 4: Polymorphism",
            "content": """### UNIT 4: Polymorphism

#### Introduction

Polymorphism allows objects to take multiple forms. It enables a single interface to represent different implementations.

This unit focuses on types of polymorphism and their applications.

#### Detailed Explanation

**Compile-Time Polymorphism**
Achieved through function overloading and operator overloading.

It allows multiple functions with the same name but different parameters.

**Run-Time Polymorphism**
Achieved through method overriding using inheritance.

It allows dynamic method binding.

#### Applications

Polymorphism is used in software development to improve flexibility and extensibility.

#### Summary

This unit explains polymorphism and its role in dynamic and flexible programming.""",
        },
        5: {
            "title": "Unit 5: Exception Handling and File Handling",
            "content": """### UNIT 5: Exception Handling and File Handling

#### Introduction

Exception handling manages runtime errors, while file handling deals with input and output operations involving files.

This unit focuses on error handling and file operations in OOP.

#### Detailed Explanation

**Exception Handling**
Exceptions are runtime errors that disrupt program flow. Mechanisms such as try-catch blocks handle these errors gracefully.

This improves program reliability.

**File Handling**
File handling involves reading and writing data to files. It allows persistent storage of data.

For example, a program can store user data in a file.

#### Applications

Exception and file handling are used in real-world applications such as databases, logging systems, and data processing.

#### Summary

This unit introduces exception and file handling, ensuring robust and reliable program execution.""",
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
