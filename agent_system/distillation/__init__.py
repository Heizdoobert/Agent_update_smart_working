"""Offline Batch Prompt Distillation Engine (Teacher-to-Student Optimizer)."""

from .distiller import DistillationEngine, PromptCandidate

__all__ = ["DistillationEngine", "PromptCandidate"]
