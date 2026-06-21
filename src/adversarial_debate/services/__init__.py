"""Service layer for adversarial-debate pipeline execution."""

from .pipeline import PipelineConfig, PipelineResult, PipelineService

__all__ = ["PipelineService", "PipelineConfig", "PipelineResult"]
