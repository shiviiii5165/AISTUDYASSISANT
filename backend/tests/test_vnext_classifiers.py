import pytest
from app.services.lesson_planner.schemas import CanonicalDomain, TeachingIntent, TopicVolatility
from app.services.lesson_planner.vnext.classifiers import (
    IntentClassifier, DomainClassifier, TopicVolatilityClassifier
)


def test_intent_classification_canonical_intents():
    # 1. Interview Prep
    assert IntentClassifier.classify("Teach dynamic programming for campus placement and LeetCode round") == TeachingIntent.INTERVIEW_PREP
    # 2. Exam Prep
    assert IntentClassifier.classify("B.Tech 3rd semester exam review on Database Normalization") == TeachingIntent.EXAM_PREP
    # 3. Project
    assert IntentClassifier.classify("Build a fullstack capstone project with Supabase") == TeachingIntent.PROJECT
    # 4. Research
    assert IntentClassifier.classify("Frontier research paper review on state of the art LLM architectures") == TeachingIntent.RESEARCH
    # 5. Implement
    assert IntentClassifier.classify("Hands-on coding lab on DFS and BFS graph traversal") == TeachingIntent.IMPLEMENT
    # 6. Practice
    assert IntentClassifier.classify("Practice exercises and problem set on integration by parts") == TeachingIntent.PRACTICE
    # 7. Assess
    assert IntentClassifier.classify("Diagnostic quiz to assess student understanding of pointers") == TeachingIntent.ASSESS
    # 8. Revise
    assert IntentClassifier.classify("Quick revision and recap of Thermodynamics") == TeachingIntent.REVISE
    # 9. Introduce
    assert IntentClassifier.classify("Introductory overview for complete beginners on Python") == TeachingIntent.INTRODUCE
    # 10. Understand
    assert IntentClassifier.classify("Deep dive into the mental model and intuition behind Backpropagation") == TeachingIntent.UNDERSTAND
    # 11. Default Teach
    assert IntentClassifier.classify("Explain Binary Search Trees to 2nd year students") == TeachingIntent.TEACH


def test_domain_classification():
    assert DomainClassifier.classify("React 19 Server Components") == CanonicalDomain.SOFTWARE_ENGINEERING
    assert DomainClassifier.classify("Binary Search Trees and AVL Trees") == CanonicalDomain.COMPUTER_SCIENCE
    assert DomainClassifier.classify("8085 Microprocessor Pin Diagram and Architecture") == CanonicalDomain.ECE
    assert DomainClassifier.classify("Three Phase Induction Motor and Synchronous Machines") == CanonicalDomain.ELECTRICAL
    assert DomainClassifier.classify("Eigenvalues and Linear Transformations") == CanonicalDomain.MATHEMATICS
    assert DomainClassifier.classify("Newton's Laws of Motion and Friction") == CanonicalDomain.PHYSICS
    assert DomainClassifier.classify("Periodic Table and Chemical Bonding") == CanonicalDomain.CHEMISTRY
    assert DomainClassifier.classify("DNA Replication and Genetics") == CanonicalDomain.BIOLOGY
    assert DomainClassifier.classify("Cardiology and Pathological Diagnosis") == CanonicalDomain.MEDICINE
    assert DomainClassifier.classify("Formative Assessment and Pedagogy") == CanonicalDomain.EDUCATION
    assert DomainClassifier.classify("Macroeconomics and Fiscal Policy") == CanonicalDomain.ECONOMICS
    assert DomainClassifier.classify("Supply Chain Management and Corporate Finance") == CanonicalDomain.BUSINESS


def test_topic_volatility_classification():
    # Low volatility (timeless)
    assert TopicVolatilityClassifier.classify("Pythagorean Theorem", CanonicalDomain.MATHEMATICS) == TopicVolatility.LOW
    assert TopicVolatilityClassifier.classify("Binary Search Algorithm", CanonicalDomain.COMPUTER_SCIENCE) == TopicVolatility.LOW
    assert TopicVolatilityClassifier.classify("Newton's Third Law", CanonicalDomain.PHYSICS) == TopicVolatility.LOW
    assert TopicVolatilityClassifier.get_freshness_weight(TopicVolatility.LOW) == 1.0

    # Medium volatility
    assert TopicVolatilityClassifier.classify("Python 3.12 syntax updates") == TopicVolatility.MEDIUM
    assert TopicVolatilityClassifier.classify("HTTP/3 and QUIC protocol") == TopicVolatility.MEDIUM
    assert TopicVolatilityClassifier.get_freshness_weight(TopicVolatility.MEDIUM) == 1.4

    # High volatility (fast frontier)
    assert TopicVolatilityClassifier.classify("React 19 Actions and Hooks") == TopicVolatility.HIGH
    assert TopicVolatilityClassifier.classify("LLM RAG Architecture with LangChain") == TopicVolatility.HIGH
    assert TopicVolatilityClassifier.get_freshness_weight(TopicVolatility.HIGH) == 2.5
