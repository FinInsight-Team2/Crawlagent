"""
Diagnosis System for CrawlAgent

This module provides intelligent failure diagnosis and recommendation engine
for the CrawlAgent multi-agent system.

Components:
- error_classifier: Categorizes failures into 5 types
- failure_analyzer: Provides detailed analysis of failures
- recommendation_engine: Suggests actionable solutions
"""

from src.diagnosis.error_classifier import ErrorClassifier, FailureCategory
from src.diagnosis.failure_analyzer import FailureAnalyzer
from src.diagnosis.recommendation_engine import RecommendationEngine

__all__ = [
    'ErrorClassifier',
    'FailureCategory',
    'FailureAnalyzer',
    'RecommendationEngine'
]
