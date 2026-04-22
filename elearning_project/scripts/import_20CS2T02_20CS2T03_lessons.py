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
    "20CS2T02": {
        1: {
            "title": "Unit 1: Vector Calculus",
            "content": """### UNIT 1: Vector Calculus

#### Introduction

Vector calculus extends the concepts of calculus to functions involving vectors. It is widely used in physics and engineering to analyze quantities that have both magnitude and direction, such as velocity, force, and electric fields. This unit introduces vector functions, differentiation, and integration in multiple dimensions.

Understanding vector calculus is essential for modeling real-world phenomena in fields like fluid dynamics, electromagnetism, and computer graphics.

#### Detailed Explanation

**Vectors and Vector Functions**
A vector is a quantity that has both magnitude and direction. Vector functions describe the motion of objects in space and are expressed in terms of components along coordinate axes.

For example, the position of a particle moving in space can be represented using a vector function of time.

**Gradient, Divergence, and Curl**
These are important operations in vector calculus. The gradient represents the rate of change of a scalar field, divergence measures the magnitude of a source or sink, and curl represents the rotation of a vector field.

These operations are widely used in analyzing physical systems such as fluid flow and electromagnetic fields.

**Line and Surface Integrals**
Line integrals are used to integrate functions along a curve, while surface integrals are used over surfaces. These concepts are important in evaluating work done by a force field.

#### Applications

Vector calculus is used in engineering fields such as electromagnetism, fluid mechanics, and robotics. It is essential for modeling physical systems involving directional quantities.

#### Summary

This unit introduces vector operations and integrals, providing tools to analyze multidimensional systems and physical phenomena.""",
        },
        2: {
            "title": "Unit 2: Multiple Integrals",
            "content": """### UNIT 2: Multiple Integrals

#### Introduction

Multiple integrals extend the concept of integration to functions of more than one variable. They are used to calculate volumes, areas, and other quantities in higher dimensions.

This unit focuses on double and triple integrals and their applications.

#### Detailed Explanation

**Double Integrals**
Double integrals are used to compute the volume under a surface in two-dimensional space. They involve integrating a function with respect to two variables.

For example, double integrals are used to calculate the area of irregular regions.

**Triple Integrals**
Triple integrals extend this concept to three dimensions and are used to compute volumes and mass of solid objects.

These integrals are useful in engineering applications involving three-dimensional objects.

**Change of Variables**
Techniques such as transformation of coordinates simplify complex integrals. For example, converting Cartesian coordinates to polar coordinates can make integration easier.

#### Applications

Multiple integrals are used in physics for calculating mass, center of gravity, and fluid flow. They are also used in engineering design and simulations.

#### Summary

This unit introduces double and triple integrals and their applications in higher-dimensional problems.""",
        },
        3: {
            "title": "Unit 3: Laplace Transforms",
            "content": """### UNIT 3: Laplace Transforms

#### Introduction

Laplace transforms are mathematical tools used to transform complex differential equations into simpler algebraic equations. They are widely used in engineering for system analysis and control systems.

This unit focuses on the definition, properties, and applications of Laplace transforms.

#### Detailed Explanation

**Definition of Laplace Transform**
The Laplace transform converts a time-domain function into a complex frequency-domain function.

\\mathcal{L}{f(t)}=\\int_0^{\\infty} e^{-st} f(t) dt

This transformation simplifies the analysis of systems governed by differential equations.

**Properties of Laplace Transforms**
Important properties include linearity, shifting, and differentiation. These properties help simplify calculations and solve equations efficiently.

**Inverse Laplace Transform**
The inverse Laplace transform is used to convert the transformed function back to the time domain.

It is essential for obtaining the final solution of a problem.

#### Applications

Laplace transforms are used in electrical circuits, control systems, and signal processing. They are essential for solving differential equations in engineering.

#### Summary

This unit introduces Laplace transforms and their properties, providing tools for solving complex engineering problems.""",
        },
        4: {
            "title": "Unit 4: Fourier Series",
            "content": """### UNIT 4: Fourier Series

#### Introduction

Fourier series represent periodic functions as sums of sine and cosine functions. This concept is fundamental in signal processing and communication systems.

This unit introduces Fourier series and their applications.

#### Detailed Explanation

**Representation of Functions**
A periodic function can be expressed as a sum of sine and cosine terms.

f(x)=a_0+\\sum_{n=1}^{\\infty}(a_n\\cos nx + b_n\\sin nx)

This representation helps analyze complex signals.

**Fourier Coefficients**
Coefficients determine the contribution of each sine and cosine term. They are calculated using integration.

**Even and Odd Functions**
Special properties of even and odd functions simplify the calculation of Fourier series.

#### Applications

Fourier series are used in signal processing, image compression, and communication systems. They are essential for analyzing periodic signals.

#### Summary

This unit introduces Fourier series and their applications in representing periodic functions.""",
        },
        5: {
            "title": "Unit 5: Probability and Statistics",
            "content": """### UNIT 5: Probability and Statistics

#### Introduction

Probability and statistics deal with the analysis of random events and data. These concepts are essential in decision-making, data analysis, and machine learning.

This unit introduces basic probability theory and statistical measures.

#### Detailed Explanation

**Probability Concepts**
Probability measures the likelihood of an event occurring. It is defined as the ratio of favorable outcomes to total outcomes.

For example, the probability of getting a head in a coin toss is 1/2.

**Random Variables**
A random variable represents possible outcomes of a random experiment. It can be discrete or continuous.

**Statistical Measures**
Measures such as mean, variance, and standard deviation describe the distribution of data.

These measures help in analyzing and interpreting data.

#### Applications

Probability and statistics are used in data science, machine learning, quality control, and risk analysis. They are essential for making informed decisions.

#### Summary

This unit introduces probability and statistical concepts, providing tools for analyzing data and uncertainty.""",
        },
    },
    "20CS2T03": {
        1: {
            "title": "Unit 1: Number Systems and Boolean Algebra",
            "content": """### UNIT 1: Number Systems and Boolean Algebra

#### Introduction

Digital systems operate using binary numbers and logical operations. This unit introduces number systems and Boolean algebra, which are fundamental for designing digital circuits.

Understanding these concepts is essential for working with computers and digital electronics.

#### Detailed Explanation

**Number Systems**
Common number systems include binary, octal, decimal, and hexadecimal. Each system has a different base and representation.

For example, binary numbers use only 0 and 1, which are used in digital circuits.

**Number Conversions**
Conversion between number systems is important for digital computations. For instance, binary to decimal conversion involves positional values.

**Boolean Algebra**
Boolean algebra deals with variables that have two values: true or false. It uses operations such as AND, OR, and NOT.

These operations form the basis of digital circuit design.

#### Applications

Number systems and Boolean algebra are used in computer architecture, digital circuit design, and programming.

#### Summary

This unit introduces number systems and Boolean algebra, forming the foundation of digital electronics.""",
        },
        2: {
            "title": "Unit 2: Logic Gates and Combinational Circuits",
            "content": """### UNIT 2: Logic Gates and Combinational Circuits

#### Introduction

Logic gates are the basic building blocks of digital circuits. Combinational circuits use these gates to perform specific operations.

This unit focuses on logic gates and their applications in circuit design.

#### Detailed Explanation

**Logic Gates**
Basic gates include AND, OR, NOT, NAND, NOR, XOR, and XNOR. Each gate performs a specific logical operation.

For example, an AND gate outputs true only when both inputs are true.

**Combinational Circuits**
These circuits depend only on current inputs. Examples include adders, subtractors, multiplexers, and decoders.

For instance, a full adder adds binary numbers and produces sum and carry outputs.

**Simplification Techniques**
Boolean expressions can be simplified using methods such as Karnaugh maps to reduce circuit complexity.

#### Applications

Combinational circuits are used in arithmetic operations, data routing, and digital systems design.

#### Summary

This unit covers logic gates and combinational circuits, essential for building digital systems.""",
        },
        3: {
            "title": "Unit 3: Sequential Circuits",
            "content": """### UNIT 3: Sequential Circuits

#### Introduction

Sequential circuits depend on both current inputs and previous states. They are used for storing information and controlling operations in digital systems.

This unit focuses on flip-flops, registers, and counters.

#### Detailed Explanation

**Flip-Flops**
Flip-flops are basic memory elements that store one bit of data. Types include SR, JK, D, and T flip-flops.

They are used in data storage and synchronization.

**Registers**
Registers are groups of flip-flops used to store multiple bits of data.

They are used in processors for temporary data storage.

**Counters**
Counters are sequential circuits used to count events. They can be synchronous or asynchronous.

#### Applications

Sequential circuits are used in memory devices, processors, and digital control systems.

#### Summary

This unit introduces sequential circuits and their components, which are essential for memory and control operations.""",
        },
        4: {
            "title": "Unit 4: Memory Devices",
            "content": """### UNIT 4: Memory Devices

#### Introduction

Memory devices are used to store data and instructions in digital systems. They play a crucial role in computer architecture.

This unit focuses on different types of memory and their characteristics.

#### Detailed Explanation

**Types of Memory**
Memory is classified into primary and secondary memory. Primary memory includes RAM and ROM, while secondary memory includes storage devices.

**RAM and ROM**
RAM is volatile memory used for temporary storage, while ROM is non-volatile and stores permanent data.

**Cache Memory**
Cache memory is a high-speed memory used to improve system performance by storing frequently accessed data.

#### Applications

Memory devices are used in computers, smartphones, and embedded systems. They are essential for data storage and processing.

#### Summary

This unit introduces memory devices and their types, highlighting their importance in digital systems.""",
        },
        5: {
            "title": "Unit 5: Programmable Logic Devices",
            "content": """### UNIT 5: Programmable Logic Devices

#### Introduction

Programmable logic devices (PLDs) allow designers to implement digital circuits using programmable components. They provide flexibility and efficiency in circuit design.

This unit focuses on different types of PLDs and their applications.

#### Detailed Explanation

**Types of PLDs**
Common PLDs include Programmable Array Logic (PAL), Programmable Logic Array (PLA), and Field Programmable Gate Arrays (FPGA).

Each type has different levels of flexibility and complexity.

**Working of PLDs**
PLDs use programmable connections to implement logic functions. Designers can configure them according to requirements.

**Advantages of PLDs**
PLDs reduce hardware complexity and allow easy modification of designs.

#### Applications

PLDs are used in embedded systems, communication systems, and digital signal processing. They are essential for modern digital design.

#### Summary

This unit introduces programmable logic devices and their role in flexible digital circuit design.""",
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
