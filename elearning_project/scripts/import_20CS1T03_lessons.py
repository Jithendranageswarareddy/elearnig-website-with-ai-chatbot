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


SUBJECT_CODE = "20CS1T03"

UNIT_CONTENT = {
    1: {
        "title": "Unit 1: Electrical Circuits Fundamentals",
        "content": """### UNIT 1: Electrical Circuits Fundamentals

#### Introduction

Electrical circuits form the backbone of all electrical and electronic systems. This unit introduces the fundamental concepts of electrical circuits, including basic components, laws, and analysis techniques. Understanding these principles is essential for analyzing and designing electrical systems used in everyday applications.

The study of electrical circuits involves understanding how current flows, how voltage behaves, and how different components such as resistors, capacitors, and inductors interact. This unit lays the foundation for advanced topics in electrical engineering.

#### Detailed Explanation

**Basic Electrical Quantities**
Electrical circuits are characterized by three primary quantities: voltage, current, and resistance. Voltage is the potential difference that drives current through a circuit, while current is the flow of electric charge. Resistance opposes the flow of current.

Ohm’s Law defines the relationship between these quantities, stating that voltage is equal to the product of current and resistance. This relationship is fundamental in analyzing circuits.

**Circuit Elements**
The main components of electrical circuits include resistors, capacitors, and inductors. Resistors limit current flow, capacitors store electrical energy in an electric field, and inductors store energy in a magnetic field.

For example, resistors are used in circuits to control current, while capacitors are used in filters and energy storage applications.

**Kirchhoff’s Laws**
Kirchhoff’s Current Law (KCL) states that the total current entering a node is equal to the total current leaving the node. Kirchhoff’s Voltage Law (KVL) states that the sum of voltages around a closed loop is zero.

These laws are essential for analyzing complex circuits and solving for unknown values.

**Series and Parallel Circuits**
In a series circuit, components are connected end-to-end, and the same current flows through all elements. In a parallel circuit, components are connected across the same voltage source, and the voltage across each component is the same.

Understanding these configurations is crucial for circuit design and analysis.

#### Applications

Electrical circuit fundamentals are used in designing household wiring systems, electronic devices, and communication systems. These principles are also applied in power distribution and control systems.

#### Summary

This unit introduces basic electrical quantities, circuit elements, and fundamental laws. These concepts are essential for understanding and analyzing electrical circuits.""",
    },
    2: {
        "title": "Unit 2: Network Theorems",
        "content": """### UNIT 2: Network Theorems

#### Introduction

Network theorems simplify the analysis of complex electrical circuits by transforming them into simpler equivalent circuits. These theorems are powerful tools that reduce computational complexity and make circuit analysis more efficient.

This unit focuses on important network theorems and their applications in solving electrical networks.

#### Detailed Explanation

**Superposition Theorem**
The superposition theorem states that in a linear circuit with multiple sources, the response can be determined by considering one source at a time while replacing others with their internal resistances.

For example, in a circuit with two voltage sources, the total current is the sum of currents due to each source individually.

**Thevenin’s Theorem**
Thevenin’s theorem states that any linear circuit can be replaced by an equivalent circuit consisting of a single voltage source and a series resistance.

This simplifies analysis, especially when studying load variations.

**Norton’s Theorem**
Norton’s theorem is similar to Thevenin’s theorem but represents the circuit as a current source in parallel with a resistance.

These equivalent representations make it easier to analyze circuits.

**Maximum Power Transfer Theorem**
This theorem states that maximum power is delivered to a load when the load resistance equals the source resistance.

This concept is widely used in communication systems and power transfer applications.

#### Applications

Network theorems are used in circuit design, fault analysis, and optimization of electrical systems. They are particularly useful in simplifying large circuits in power systems and electronics.

#### Summary

This unit covers important network theorems that simplify circuit analysis. These theorems are essential tools for engineers working with complex electrical networks.""",
    },
    3: {
        "title": "Unit 3: AC Circuits",
        "content": """### UNIT 3: AC Circuits

#### Introduction

Alternating current (AC) circuits are widely used in power systems due to their efficiency in transmission and distribution. Unlike direct current (DC), AC changes its magnitude and direction periodically.

This unit introduces AC fundamentals, waveform analysis, and circuit behavior involving resistors, capacitors, and inductors.

#### Detailed Explanation

**AC Waveforms**
AC voltage and current are typically represented as sinusoidal waveforms. Important parameters include amplitude, frequency, and phase.

For example, the standard power supply in homes is a sinusoidal AC waveform with a frequency of 50 Hz.

**Impedance and Reactance**
In AC circuits, resistance is extended to impedance, which includes both resistance and reactance. Capacitive reactance and inductive reactance affect how current flows in the circuit.

These concepts are essential for analyzing AC circuits.

**Power in AC Circuits**
Power in AC circuits is categorized into active power, reactive power, and apparent power. The power factor indicates the efficiency of power usage.

A high power factor indicates efficient energy utilization.

#### Applications

AC circuits are used in power generation, transmission, and distribution systems. They are also used in household appliances, industrial machinery, and communication systems.

#### Summary

This unit introduces AC circuit concepts, including waveforms, impedance, and power analysis. These are essential for understanding modern electrical systems.""",
    },
    4: {
        "title": "Unit 4: Electrical Machines",
        "content": """### UNIT 4: Electrical Machines

#### Introduction

Electrical machines convert electrical energy into mechanical energy and vice versa. They are essential components in industries and daily life.

This unit focuses on the working principles and types of electrical machines.

#### Detailed Explanation

**DC Machines**
DC machines include DC generators and motors. They operate based on electromagnetic principles and are used in applications requiring precise speed control.

**Transformers**
Transformers transfer electrical energy between circuits using electromagnetic induction. They are used to step up or step down voltage levels in power systems.

For example, transformers are used in power transmission to reduce energy losses.

**Induction Motors**
Induction motors are widely used in industries due to their simplicity and reliability. They operate on the principle of electromagnetic induction.

#### Applications

Electrical machines are used in industries, transportation systems, household appliances, and power plants. They are essential for energy conversion and utilization.

#### Summary

This unit covers different types of electrical machines and their working principles. These machines are crucial for energy conversion in various applications.""",
    },
    5: {
        "title": "Unit 5: Electrical Measurements",
        "content": """### UNIT 5: Electrical Measurements

#### Introduction

Electrical measurements involve measuring electrical quantities such as voltage, current, resistance, and power. Accurate measurement is essential for system analysis, maintenance, and control.

This unit introduces measuring instruments and techniques used in electrical engineering.

#### Detailed Explanation

**Measuring Instruments**
Common instruments include ammeters, voltmeters, and wattmeters. These devices are used to measure current, voltage, and power respectively.

For example, an ammeter is connected in series, while a voltmeter is connected in parallel.

**Measurement Techniques**
Different techniques are used depending on the quantity being measured. Bridge circuits, such as Wheatstone bridge, are used for precise resistance measurement.

**Errors in Measurement**
Measurement errors can arise due to instrument limitations, environmental factors, or human mistakes. Understanding and minimizing errors is important for accurate results.

#### Applications

Electrical measurements are used in testing, maintenance, and quality control of electrical systems. They are essential in laboratories and industrial environments.

#### Summary

This unit introduces electrical measuring instruments and techniques. Accurate measurement is crucial for reliable operation and analysis of electrical systems.""",
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
            unit_changed = False
            if unit.title != data["title"]:
                unit.title = data["title"]
                unit_changed = True
            if unit.content != data["content"]:
                unit.content = data["content"]
                unit_changed = True
            if not unit.is_active:
                unit.is_active = True
                unit_changed = True
            if unit_changed:
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
            lesson_changed = False
            if lesson.unit_id != unit.id:
                lesson.unit = unit
                lesson_changed = True
            if lesson.title != data["title"]:
                lesson.title = data["title"]
                lesson_changed = True
            if lesson.content != data["content"]:
                lesson.content = data["content"]
                lesson_changed = True
            if not lesson.is_active:
                lesson.is_active = True
                lesson_changed = True
            if lesson_changed:
                lesson.save(update_fields=["unit", "title", "content", "is_active"])
                lesson_updated += 1

    total_active_lessons = Lesson.objects.filter(subject=subject, is_active=True).count()

    print(
        {
            "subject_code": SUBJECT_CODE,
            "units_created": unit_created,
            "units_updated": unit_updated,
            "lessons_created": lesson_created,
            "lessons_updated": lesson_updated,
            "total_active_lessons_for_subject": total_active_lessons,
        }
    )


if __name__ == "__main__":
    main()
