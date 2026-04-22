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
    "20CS6T01": {
        1: {
            "title": "Unit 1: Introduction to ML",
            "content": '''### UNIT 1: Introduction to ML

#### Introduction

Machine Learning (ML) is a subset of Artificial Intelligence that focuses on developing algorithms that enable computers to learn from data and make predictions or decisions without being explicitly programmed. It plays a crucial role in modern technology, powering applications such as recommendation systems, image recognition, and predictive analytics.

The primary goal of machine learning is to build models that can generalize from past data and perform well on unseen data. This unit introduces the basic concepts, types, and workflow of machine learning.

#### Detailed Explanation

**Concept of Machine Learning**
Machine learning involves training a model using data so that it can identify patterns and relationships. Instead of writing explicit rules, developers provide data and let the algorithm learn from it.

For example, an email spam filter learns to classify emails based on features such as keywords and sender information.

**Types of Machine Learning**
Machine learning is broadly classified into supervised learning, unsupervised learning, and reinforcement learning. Each type is suited for different kinds of problems.

Supervised learning uses labeled data, while unsupervised learning identifies hidden patterns in unlabeled data.

**ML Workflow**
The typical workflow includes data collection, preprocessing, model training, evaluation, and deployment. Each step is critical to ensure accurate and reliable predictions.

#### Applications

Machine learning is used in healthcare for disease prediction, finance for fraud detection, and e-commerce for recommendation systems.

#### Summary

This unit introduces machine learning concepts, types, and workflow, providing a foundation for advanced topics.''',
        },
        2: {
            "title": "Unit 2: Supervised Learning",
            "content": '''### UNIT 2: Supervised Learning

#### Introduction

Supervised learning is a type of machine learning where models are trained using labeled data. The goal is to learn a mapping from input features to output labels.

This unit focuses on classification and regression techniques.

#### Detailed Explanation

**Classification Algorithms**
Classification involves predicting discrete labels. Algorithms such as decision trees, k-nearest neighbors, and support vector machines are commonly used.

For example, classifying emails as spam or not spam is a classification problem.

**Regression Algorithms**
Regression involves predicting continuous values. Linear regression is a widely used technique.

For example, predicting house prices based on features like size and location.

**Overfitting and Underfitting**
Overfitting occurs when a model learns noise instead of patterns, while underfitting occurs when a model fails to capture patterns.

Balancing these is essential for good performance.

#### Applications

Supervised learning is used in medical diagnosis, stock price prediction, and speech recognition.

#### Summary

This unit covers supervised learning techniques and challenges in model training.''',
        },
        3: {
            "title": "Unit 3: Unsupervised Learning",
            "content": '''### UNIT 3: Unsupervised Learning

#### Introduction

Unsupervised learning deals with unlabeled data and aims to discover hidden patterns or structures.

This unit focuses on clustering and dimensionality reduction techniques.

#### Detailed Explanation

**Clustering Techniques**
Clustering groups similar data points together. Algorithms such as k-means and hierarchical clustering are widely used.

For example, grouping customers based on purchasing behavior.

**Dimensionality Reduction**
Techniques like Principal Component Analysis (PCA) reduce the number of features while preserving important information.

This improves computational efficiency.

#### Applications

Unsupervised learning is used in market segmentation, anomaly detection, and data compression.

#### Summary

This unit introduces unsupervised learning methods for pattern discovery.''',
        },
        4: {
            "title": "Unit 4: Neural Networks",
            "content": '''### UNIT 4: Neural Networks

#### Introduction

Neural networks are computational models inspired by the human brain. They consist of interconnected nodes that process information in layers.

This unit introduces the structure and working of neural networks.

#### Detailed Explanation

**Structure of Neural Networks**
A neural network consists of input, hidden, and output layers. Each connection has a weight that is adjusted during training.

Activation functions introduce non-linearity into the model.

**Training of Neural Networks**
Training involves adjusting weights using algorithms such as backpropagation.

The goal is to minimize the error between predicted and actual outputs.

**Deep Learning**
Deep learning involves neural networks with multiple hidden layers.

It is used in complex tasks such as image and speech recognition.

#### Applications

Neural networks are used in computer vision, natural language processing, and autonomous systems.

#### Summary

This unit explains neural networks and their role in advanced machine learning.''',
        },
        5: {
            "title": "Unit 5: Model Evaluation",
            "content": '''### UNIT 5: Model Evaluation

#### Introduction

Model evaluation is essential to measure the performance of machine learning models. It ensures that models generalize well to new data.

This unit focuses on evaluation metrics and validation techniques.

#### Detailed Explanation

**Evaluation Metrics**
Metrics such as accuracy, precision, recall, and F1-score are used for classification problems.

For regression, metrics like mean squared error are used.

**Cross-Validation**
Cross-validation techniques help assess model performance by dividing data into training and testing sets.

**Confusion Matrix**
A confusion matrix provides detailed insights into classification performance.

#### Applications

Model evaluation is used in all machine learning applications to ensure reliability and accuracy.

#### Summary

This unit introduces evaluation techniques for assessing model performance.''',
        },
    },
    "20CS6T02": {
        1: {
            "title": "Unit 1: Introduction to Distributed Systems",
            "content": '''### UNIT 1: Introduction to Distributed Systems

#### Introduction

A distributed system is a collection of independent computers that appear as a single system to users. These systems work together to achieve a common goal.

This unit introduces the characteristics and advantages of distributed systems.

#### Detailed Explanation

**Characteristics**
Distributed systems provide resource sharing, scalability, and fault tolerance.

They enable multiple systems to work together efficiently.

**Types of Distributed Systems**
Examples include client-server systems and peer-to-peer systems.

#### Applications

Used in cloud computing, distributed databases, and large-scale applications.

#### Summary

This unit introduces distributed system concepts.''',
        },
        2: {
            "title": "Unit 2: Communication Models",
            "content": '''### UNIT 2: Communication Models

#### Introduction

Communication is essential in distributed systems.

#### Detailed Explanation

**Message Passing**
Processes communicate by sending messages.

**Remote Procedure Calls (RPC)**
Allows calling functions on remote systems.

#### Applications

Used in distributed applications.

#### Summary

This unit explains communication models.''',
        },
        3: {
            "title": "Unit 3: Synchronization",
            "content": '''### UNIT 3: Synchronization

#### Introduction

Synchronization ensures coordination among processes.

#### Detailed Explanation

**Clock Synchronization**
Ensures consistent time across systems.

**Mutual Exclusion**
Prevents conflicts.

#### Applications

Used in distributed computing.

#### Summary

This unit explains synchronization.''',
        },
        4: {
            "title": "Unit 4: Distributed File Systems",
            "content": '''### UNIT 4: Distributed File Systems

#### Introduction

Provides file access across systems.

#### Detailed Explanation

**File Sharing**
Allows access to files.

**Consistency Models**
Ensure data consistency.

#### Applications

Used in cloud storage.

#### Summary

This unit explains DFS.''',
        },
        5: {
            "title": "Unit 5: Fault Tolerance",
            "content": '''### UNIT 5: Fault Tolerance

#### Introduction

Ensures system reliability.

#### Detailed Explanation

**Failure Types**
Crash and network failures.

**Recovery Techniques**
Replication and backup.

#### Applications

Used in reliable systems.

#### Summary

This unit explains fault tolerance.''',
        },
    },
    "20CS6T03": {
        1: {
            "title": "Unit 1: Cryptography Basics",
            "content": '''### UNIT 1: Cryptography Basics

#### Introduction

Cryptography secures communication.

#### Detailed Explanation

**Concepts**
Encryption and decryption.

**Goals**
Confidentiality, integrity, authentication.

#### Applications

Used in secure communication.

#### Summary

This unit explains cryptography basics.''',
        },
        2: {
            "title": "Unit 2: Symmetric Key Cryptography",
            "content": '''### UNIT 2: Symmetric Key Cryptography

#### Introduction

Uses a single key.

#### Detailed Explanation

**Algorithms**
AES, DES.

#### Applications

Used in secure systems.

#### Summary

This unit explains symmetric crypto.''',
        },
        3: {
            "title": "Unit 3: Asymmetric Cryptography",
            "content": '''### UNIT 3: Asymmetric Cryptography

#### Introduction

Uses public and private keys.

#### Detailed Explanation

**Algorithms**
RSA.

#### Applications

Used in digital signatures.

#### Summary

This unit explains asymmetric crypto.''',
        },
        4: {
            "title": "Unit 4: Network Security Protocols",
            "content": '''### UNIT 4: Network Security Protocols

#### Introduction

Ensure secure communication.

#### Detailed Explanation

**Protocols**
SSL/TLS.

#### Applications

Used in internet security.

#### Summary

This unit explains protocols.''',
        },
        5: {
            "title": "Unit 5: Cyber Security Practices",
            "content": '''### UNIT 5: Cyber Security Practices

#### Introduction

Protect systems.

#### Detailed Explanation

**Practices**
Firewalls, antivirus.

#### Applications

Used in organizations.

#### Summary

This unit explains security practices.''',
        },
    },
    "20CS6T04": {
        1: {
            "title": "Unit 1: Mobile Communication Basics",
            "content": '''### UNIT 1: Mobile Communication Basics

#### Introduction

Mobile computing enables communication on the move.

#### Detailed Explanation

**Concepts**
Cellular networks.

#### Applications

Used in smartphones.

#### Summary

This unit explains basics.''',
        },
        2: {
            "title": "Unit 2: Wireless Networks",
            "content": '''### UNIT 2: Wireless Networks

#### Introduction

Enable wireless communication.

#### Detailed Explanation

**Technologies**
Wi-Fi, Bluetooth.

#### Applications

Used in networking.

#### Summary

This unit explains wireless networks.''',
        },
        3: {
            "title": "Unit 3: Mobile IP",
            "content": '''### UNIT 3: Mobile IP

#### Introduction

Supports mobility.

#### Detailed Explanation

**Concepts**
Home and foreign agents.

#### Applications

Used in mobile systems.

#### Summary

This unit explains mobile IP.''',
        },
        4: {
            "title": "Unit 4: Mobile Application Development",
            "content": '''### UNIT 4: Mobile Application Development

#### Introduction

Develops mobile apps.

#### Detailed Explanation

**Platforms**
Android, iOS.

#### Applications

Used in app development.

#### Summary

This unit explains mobile apps.''',
        },
        5: {
            "title": "Unit 5: Security in Mobile Computing",
            "content": '''### UNIT 5: Security in Mobile Computing

#### Introduction

Ensures mobile security.

#### Detailed Explanation

**Threats**
Malware.

**Solutions**
Encryption.

#### Applications

Used in mobile systems.

#### Summary

This unit explains mobile security.''',
        },
    },
    "20CS7T01": {
        1: {
            "title": "Unit 1: Big Data Fundamentals",
            "content": '''### UNIT 1: Big Data Fundamentals

#### Introduction

Big Data refers to extremely large and complex datasets that cannot be processed efficiently using traditional data processing tools. With the rapid growth of digital technologies, massive amounts of structured, semi-structured, and unstructured data are generated daily from sources such as social media, sensors, and enterprise systems. This unit introduces the fundamental concepts of Big Data, including its characteristics, challenges, and importance in modern computing.

Understanding Big Data is essential for organizations to extract meaningful insights and make data-driven decisions. It enables businesses to improve efficiency, enhance customer experiences, and gain competitive advantages.

#### Detailed Explanation

**Characteristics of Big Data**
Big Data is commonly described using the five Vs: Volume, Velocity, Variety, Veracity, and Value. Volume refers to the large size of data, velocity indicates the speed of data generation, and variety includes different data types such as text, images, and videos.

For example, social media platforms generate massive volumes of data every second, which need to be processed in real time.

**Sources of Big Data**
Data is generated from multiple sources such as IoT devices, online transactions, and enterprise applications.

These sources contribute to the diversity and complexity of Big Data.

**Challenges in Big Data**
Challenges include data storage, processing, security, and data quality. Traditional databases are not sufficient to handle such large datasets, leading to the development of distributed systems.

#### Applications

Big Data is used in healthcare for predictive analysis, finance for fraud detection, and marketing for customer behavior analysis.

#### Summary

This unit introduces the concept of Big Data, its characteristics, and challenges, highlighting its importance in modern applications.''',
        },
        2: {
            "title": "Unit 2: Hadoop Ecosystem",
            "content": '''### UNIT 2: Hadoop Ecosystem

#### Introduction

The Hadoop ecosystem is a framework designed to store and process large datasets in a distributed environment. It provides scalable and fault-tolerant solutions for Big Data processing.

This unit focuses on the components of the Hadoop ecosystem and their roles.

#### Detailed Explanation

**Hadoop Distributed File System (HDFS)**
HDFS is a distributed file system that stores data across multiple machines. It ensures data reliability through replication.

For example, data is divided into blocks and stored across different nodes.

**YARN (Yet Another Resource Negotiator)**
YARN manages resources and schedules tasks in a Hadoop cluster.

It enables efficient utilization of system resources.

**Hadoop Ecosystem Tools**
Tools such as Hive, Pig, and HBase extend Hadoop’s capabilities. Hive provides SQL-like querying, while Pig simplifies data processing.

#### Applications

Hadoop is used in data warehousing, log analysis, and large-scale data processing.

#### Summary

This unit introduces Hadoop components and their role in Big Data processing.''',
        },
        3: {
            "title": "Unit 3: MapReduce",
            "content": '''### UNIT 3: MapReduce

#### Introduction

MapReduce is a programming model used for processing large datasets in parallel across distributed systems. It simplifies data processing by dividing tasks into smaller sub-tasks.

This unit focuses on the working of MapReduce.

#### Detailed Explanation

**Map Phase**
In this phase, input data is divided into smaller chunks, and each chunk is processed independently to produce key-value pairs.

**Reduce Phase**
The reduce phase aggregates results from the map phase to produce final output.

**Advantages of MapReduce**
It provides scalability, fault tolerance, and efficient processing of large datasets.

#### Applications

MapReduce is used in data analysis, indexing, and distributed computing tasks.

#### Summary

This unit explains the MapReduce model and its role in distributed data processing.''',
        },
        4: {
            "title": "Unit 4: Spark",
            "content": '''### UNIT 4: Spark

#### Introduction

Apache Spark is a fast and general-purpose cluster computing system for Big Data processing. It overcomes the limitations of Hadoop MapReduce by providing in-memory computation.

This unit focuses on Spark architecture and features.

#### Detailed Explanation

**Spark Architecture**
Spark consists of a driver program and worker nodes. It processes data in memory, which improves speed.

It supports various libraries such as Spark SQL, MLlib, and GraphX.

**Advantages of Spark**
Spark is faster than MapReduce due to in-memory processing. It supports real-time data processing and machine learning.

#### Applications

Spark is used in real-time analytics, machine learning, and stream processing.

#### Summary

This unit introduces Spark and its advantages in Big Data processing.''',
        },
        5: {
            "title": "Unit 5: Data Analytics Applications",
            "content": '''### UNIT 5: Data Analytics Applications

#### Introduction

Data analytics involves extracting meaningful insights from data to support decision-making. Big Data analytics enables advanced analysis using large datasets.

This unit focuses on applications of data analytics.

#### Detailed Explanation

**Types of Analytics**
Descriptive, predictive, and prescriptive analytics are used to analyze data at different levels.

For example, predictive analytics forecasts future trends.

**Tools and Techniques**
Tools such as Hadoop, Spark, and machine learning algorithms are used.

#### Applications

Applications include business intelligence, healthcare analysis, and recommendation systems.

#### Summary

This unit highlights applications of Big Data analytics in various domains.''',
        },
    },
    "20CS7T02": {
        1: {
            "title": "Unit 1: Cloud Fundamentals",
            "content": '''### UNIT 1: Cloud Fundamentals

#### Introduction

Cloud computing provides on-demand access to computing resources over the internet. It eliminates the need for local infrastructure and enables scalable and flexible computing.

This unit introduces cloud concepts and characteristics.

#### Detailed Explanation

**Characteristics of Cloud Computing**
Key features include scalability, elasticity, and pay-as-you-go pricing.

Users can access resources anytime and anywhere.

**Benefits of Cloud Computing**
Cloud computing reduces costs and improves efficiency.

#### Applications

Used in web hosting, data storage, and enterprise applications.

#### Summary

This unit introduces cloud fundamentals.''',
        },
        2: {
            "title": "Unit 2: Virtualization",
            "content": '''### UNIT 2: Virtualization

#### Introduction

Virtualization is the process of creating virtual versions of physical resources.

#### Detailed Explanation

**Types of Virtualization**
Includes server, storage, and network virtualization.

**Hypervisors**
Manage virtual machines.

#### Applications

Used in cloud infrastructure.

#### Summary

This unit explains virtualization.''',
        },
        3: {
            "title": "Unit 3: Cloud Services Models",
            "content": '''### UNIT 3: Cloud Services Models

#### Introduction

Cloud services are categorized into different models.

#### Detailed Explanation

**IaaS, PaaS, SaaS**
Each model provides different levels of control.

#### Applications

Used in cloud services.

#### Summary

This unit explains service models.''',
        },
        4: {
            "title": "Unit 4: Cloud Deployment Models",
            "content": '''### UNIT 4: Cloud Deployment Models

#### Introduction

Cloud deployment models define how cloud services are deployed.

#### Detailed Explanation

**Types**
Public, private, hybrid clouds.

#### Applications

Used in organizations.

#### Summary

This unit explains deployment models.''',
        },
        5: {
            "title": "Unit 5: Cloud Security",
            "content": '''### UNIT 5: Cloud Security

#### Introduction

Cloud security ensures data protection.

#### Detailed Explanation

**Threats and Solutions**
Includes encryption and access control.

#### Applications

Used in secure cloud systems.

#### Summary

This unit explains cloud security.''',
        },
    },
    "20CS7T03": {
        1: {
            "title": "Unit 1: IoT Fundamentals",
            "content": '''### UNIT 1: IoT Fundamentals

#### Introduction

IoT connects devices for data exchange.

#### Detailed Explanation

**Concepts**
Smart devices and connectivity.

#### Applications

Used in smart homes.

#### Summary

This unit explains IoT basics.''',
        },
        2: {
            "title": "Unit 2: Sensors and Devices",
            "content": '''### UNIT 2: Sensors and Devices

#### Introduction

Sensors collect data.

#### Detailed Explanation

**Types of Sensors**
Temperature, motion sensors.

#### Applications

Used in monitoring systems.

#### Summary

This unit explains sensors.''',
        },
        3: {
            "title": "Unit 3: Communication Protocols",
            "content": '''### UNIT 3: Communication Protocols

#### Introduction

Protocols enable communication.

#### Detailed Explanation

**Protocols**
MQTT, HTTP.

#### Applications

Used in IoT systems.

#### Summary

This unit explains protocols.''',
        },
        4: {
            "title": "Unit 4: IoT Architecture",
            "content": '''### UNIT 4: IoT Architecture

#### Introduction

Defines system structure.

#### Detailed Explanation

**Layers**
Perception, network, application.

#### Applications

Used in IoT design.

#### Summary

This unit explains architecture.''',
        },
        5: {
            "title": "Unit 5: IoT Applications",
            "content": '''### UNIT 5: IoT Applications

#### Introduction

IoT is widely used.

#### Detailed Explanation

**Applications**
Smart cities, healthcare.

#### Applications

Used in real-world systems.

#### Summary

This unit explains IoT applications.''',
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
