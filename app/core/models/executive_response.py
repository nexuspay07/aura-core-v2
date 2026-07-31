"""Stable, presentation-ready contract for Aura executive intelligence."""

from typing import Any

from pydantic import BaseModel, Field


class ExecutiveResponse(BaseModel):
    title: str = "Executive Intelligence Report"
    executive_summary: str = ""
    situation_overview: str = ""
    business_context: dict[str, Any] = Field(default_factory=dict)
    strategic_analysis: dict[str, Any] = Field(default_factory=dict)
    market_intelligence: dict[str, Any] = Field(default_factory=dict)
    competitive_intelligence: dict[str, Any] = Field(default_factory=dict)
    key_risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommended_strategy: dict[str, Any] = Field(default_factory=dict)
    implementation_roadmap: list[dict[str, Any]] = Field(default_factory=list)
    plan_30_60_90: list[dict[str, Any]] = Field(default_factory=list)
    kpis: list[dict[str, Any]] = Field(default_factory=list)
    confidence: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    suggested_next_actions: list[str] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)
