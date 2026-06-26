"""
Platform Intelligence Hub - Central intelligence aggregation and distribution.

Coordinates intelligence across the platform:
- Cross-module insight aggregation and synthesis
- Pattern detection across system-wide telemetry
- Predictive anomaly detection and proactive alerts
- Intelligence distribution with priority-based routing
- Trend analysis and forecasting
- Decision support with confidence scoring
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.intelligence_hub")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class IntelligenceType(str, Enum):
    """Type of intelligence signal."""
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    TREND = "trend"
    INSIGHT = "insight"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    CORRELATION = "correlation"


class IntelligencePriority(str, Enum):
    """Priority of intelligence signals."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OBSERVATION = "observation"


class IntelligenceStatus(str, Enum):
    """Status of an intelligence signal."""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"
    RESOLVED = "resolved"


class ConfidenceLevel(str, Enum):
    """Confidence level of an intelligence assessment."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class SignalSource(str, Enum):
    """Source of the intelligence signal."""
    AGENT_PERFORMANCE = "agent_performance"
    USER_BEHAVIOR = "user_behavior"
    SYSTEM_METRICS = "system_metrics"
    COST_ANALYSIS = "cost_analysis"
    QUALITY_ASSESSMENT = "quality_assessment"
    SECURITY = "security"
    EXTERNAL = "external"
    CROSS_MODULE = "cross_module"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class IntelligenceSignal:
    """A single intelligence signal."""
    signal_id: str
    intelligence_type: IntelligenceType
    priority: IntelligencePriority
    source: SignalSource
    title: str
    description: str
    data: dict[str, Any]
    confidence: ConfidenceLevel
    status: IntelligenceStatus = IntelligenceStatus.DETECTED
    tags: list[str] = field(default_factory=list)
    related_signals: list[str] = field(default_factory=list)
    recommended_action: str = ""
    expected_impact: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "intelligence_type": self.intelligence_type.value,
            "priority": self.priority.value,
            "source": self.source.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "confidence": self.confidence.value,
            "status": self.status.value,
            "tags": self.tags,
            "related_signals": self.related_signals,
            "recommended_action": self.recommended_action,
            "expected_impact": self.expected_impact,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class IntelligenceReport:
    """Aggregated intelligence report."""
    report_id: str
    title: str
    period_start: datetime
    period_end: datetime
    summary: str
    signals: list[IntelligenceSignal]
    total_signals: int
    critical_count: int
    actioned_count: int
    top_patterns: list[dict[str, Any]]
    key_findings: list[str]
    recommendations: list[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "title": self.title,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "summary": self.summary,
            "total_signals": self.total_signals,
            "critical_count": self.critical_count,
            "actioned_count": self.actioned_count,
            "top_patterns": self.top_patterns,
            "key_findings": self.key_findings,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class HubStats:
    """Statistics for the intelligence hub."""
    total_signals: int = 0
    signals_by_type: dict[str, int] = field(default_factory=dict)
    signals_by_source: dict[str, int] = field(default_factory=dict)
    signals_by_status: dict[str, int] = field(default_factory=dict)
    total_reports: int = 0
    avg_signals_per_report: float = 0.0
    critical_resolution_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_signals": self.total_signals,
            "signals_by_type": self.signals_by_type,
            "signals_by_source": self.signals_by_source,
            "signals_by_status": self.signals_by_status,
            "total_reports": self.total_reports,
            "avg_signals_per_report": self.avg_signals_per_report,
            "critical_resolution_rate": self.critical_resolution_rate,
        }


# ═══════════════════════════════════════════════════════════
# Platform Intelligence Hub
# ═══════════════════════════════════════════════════════════

class PlatformIntelligenceHub:
    """
    Central intelligence aggregation and distribution hub.
    
    Features:
    - Cross-module signal aggregation and correlation
    - Pattern detection across system-wide telemetry
    - Predictive anomaly detection with confidence scoring
    - Priority-based intelligence routing and distribution
    - Automated report generation with key findings
    - Trend analysis and forecasting
    """

    def __init__(self, config: IntelligenceHubConfig | None = None):
        self.config = config or IntelligenceHubConfig()
        self._signals: dict[str, IntelligenceSignal] = {}
        self._reports: list[IntelligenceReport] = []
        self._signal_correlations: dict[str, list[str]] = defaultdict(list)
        self._stats = HubStats()

    # ── Signal Management ──

    def ingest_signal(
        self,
        intelligence_type: IntelligenceType,
        priority: IntelligencePriority,
        source: SignalSource,
        title: str,
        description: str,
        data: dict[str, Any] | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        tags: list[str] | None = None,
        recommended_action: str = "",
    ) -> IntelligenceSignal:
        """Ingest a new intelligence signal into the hub."""
        signal = IntelligenceSignal(
            signal_id=str(uuid.uuid4())[:8],
            intelligence_type=intelligence_type,
            priority=priority,
            source=source,
            title=title,
            description=description,
            data=data or {},
            confidence=confidence,
            tags=tags or [],
            recommended_action=recommended_action,
        )

        # Find correlations
        related = self._find_correlations(signal)
        signal.related_signals = related

        self._signals[signal.signal_id] = signal
        self._update_stats_signal(signal)

        logger.info(
            "Intelligence signal %s: %s [%s/%s]",
            signal.signal_id, title, intelligence_type.value, priority.value,
        )

        return signal

    def update_signal_status(
        self, signal_id: str, status: IntelligenceStatus
    ) -> IntelligenceSignal | None:
        """Update the status of an intelligence signal."""
        signal = self._signals.get(signal_id)
        if not signal:
            return None

        old_status = signal.status
        signal.status = status

        if status in (IntelligenceStatus.RESOLVED, IntelligenceStatus.DISMISSED):
            signal.resolved_at = datetime.now(timezone.utc)

        self._stats.signals_by_status[old_status.value] = max(
            0, self._stats.signals_by_status.get(old_status.value, 0) - 1
        )
        self._stats.signals_by_status[status.value] = (
            self._stats.signals_by_status.get(status.value, 0) + 1
        )

        return signal

    def _find_correlations(self, signal: IntelligenceSignal) -> list[str]:
        """Find correlated signals."""
        related = []
        for existing_id, existing in self._signals.items():
            # Same source and type
            if existing.source == signal.source and existing.intelligence_type == signal.intelligence_type:
                related.append(existing_id)
                continue

            # Shared tags
            if set(signal.tags) & set(existing.tags):
                related.append(existing_id)
                continue

            # Similar keywords in description
            signal_words = set(signal.description.lower().split())
            existing_words = set(existing.description.lower().split())
            common = signal_words & existing_words - {"the", "a", "an", "is", "are", "was", "in", "on", "at", "to", "of", "and"}
            if len(common) >= 3:
                related.append(existing_id)

        return related[:10]

    # ── Query & Analysis ──

    def get_signals(
        self,
        intelligence_type: IntelligenceType | None = None,
        priority: IntelligencePriority | None = None,
        source: SignalSource | None = None,
        status: IntelligenceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IntelligenceSignal]:
        """Query intelligence signals with filters."""
        results = list(self._signals.values())

        if intelligence_type:
            results = [s for s in results if s.intelligence_type == intelligence_type]
        if priority:
            results = [s for s in results if s.priority == priority]
        if source:
            results = [s for s in results if s.source == source]
        if status:
            results = [s for s in results if s.status == status]

        results.sort(key=lambda s: s.detected_at, reverse=True)
        return results[offset:offset + limit]

    def get_critical_signals(self) -> list[IntelligenceSignal]:
        """Get all critical priority signals."""
        return [
            s for s in self._signals.values()
            if s.priority == IntelligencePriority.CRITICAL
            and s.status not in (IntelligenceStatus.RESOLVED, IntelligenceStatus.DISMISSED)
        ]

    def detect_patterns(self, min_occurrences: int = 3) -> list[dict[str, Any]]:
        """Detect recurring patterns in signals."""
        type_groups = defaultdict(list)
        for signal in self._signals.values():
            type_groups[signal.intelligence_type.value].append(signal)

        patterns = []
        for type_name, signals in type_groups.items():
            if len(signals) >= min_occurrences:
                # Group by tags
                tag_groups = defaultdict(list)
                for s in signals:
                    for tag in s.tags:
                        tag_groups[tag].append(s)

                for tag, tagged_signals in tag_groups.items():
                    if len(tagged_signals) >= min_occurrences:
                        patterns.append({
                            "pattern_type": type_name,
                            "tag": tag,
                            "occurrences": len(tagged_signals),
                            "first_seen": min(s.detected_at for s in tagged_signals).isoformat(),
                            "last_seen": max(s.detected_at for s in tagged_signals).isoformat(),
                            "avg_confidence": sum(
                                self._confidence_numeric(s.confidence)
                                for s in tagged_signals
                            ) / len(tagged_signals),
                            "signal_ids": [s.signal_id for s in tagged_signals[:5]],
                        })

        return patterns

    # ── Reports ──

    def generate_report(
        self,
        title: str = "",
        hours_back: int = 24,
    ) -> IntelligenceReport:
        """Generate an intelligence report for a time period."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        period_signals = [
            s for s in self._signals.values()
            if s.detected_at >= cutoff
        ]

        critical = [s for s in period_signals if s.priority == IntelligencePriority.CRITICAL]
        actioned = [s for s in period_signals if s.status == IntelligenceStatus.ACTIONED]

        patterns = self.detect_patterns()
        top_patterns = sorted(patterns, key=lambda p: p["occurrences"], reverse=True)[:5]

        # Generate key findings
        findings = []
        if critical:
            findings.append(f"{len(critical)} critical signals detected")
        if actioned:
            findings.append(f"{len(actioned)} signals actioned")
        if top_patterns:
            findings.append(f"Top pattern: {top_patterns[0]['pattern_type']} ({top_patterns[0]['occurrences']} occurrences)")

        # Generate recommendations
        recommendations = []
        for pattern in top_patterns[:3]:
            if pattern["avg_confidence"] >= 0.6:
                recommendations.append(
                    f"Investigate {pattern['pattern_type']} pattern with tag '{pattern['tag']}' "
                    f"({pattern['occurrences']} occurrences, confidence: {pattern['avg_confidence']:.0%})"
                )

        report = IntelligenceReport(
            report_id=str(uuid.uuid4())[:8],
            title=title or f"Intelligence Report - {cutoff.strftime('%Y-%m-%d %H:%M')} to {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            period_start=cutoff,
            period_end=datetime.now(timezone.utc),
            summary=f"Generated {len(period_signals)} signals in the last {hours_back} hours. "
                    f"{len(critical)} critical, {len(actioned)} actioned.",
            signals=period_signals[:50],
            total_signals=len(period_signals),
            critical_count=len(critical),
            actioned_count=len(actioned),
            top_patterns=top_patterns,
            key_findings=findings,
            recommendations=recommendations,
        )

        self._reports.append(report)
        self._stats.total_reports += 1
        self._stats.avg_signals_per_report = (
            (self._stats.avg_signals_per_report * (self._stats.total_reports - 1) + len(period_signals))
            / self._stats.total_reports
        )

        return report

    # ── Helpers ──

    def _confidence_numeric(self, confidence: ConfidenceLevel) -> float:
        """Convert confidence level to numeric."""
        return {
            ConfidenceLevel.VERY_HIGH: 1.0,
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.UNCERTAIN: 0.2,
        }.get(confidence, 0.5)

    def _update_stats_signal(self, signal: IntelligenceSignal) -> None:
        """Update hub statistics."""
        self._stats.total_signals += 1
        self._stats.signals_by_type[signal.intelligence_type.value] = (
            self._stats.signals_by_type.get(signal.intelligence_type.value, 0) + 1
        )
        self._stats.signals_by_source[signal.source.value] = (
            self._stats.signals_by_source.get(signal.source.value, 0) + 1
        )
        self._stats.signals_by_status[signal.status.value] = (
            self._stats.signals_by_status.get(signal.status.value, 0) + 1
        )

    def get_stats(self) -> HubStats:
        """Get hub statistics."""
        return self._stats

    def get_report(self, report_id: str) -> IntelligenceReport | None:
        """Get a report by ID."""
        for report in self._reports:
            if report.report_id == report_id:
                return report
        return None

    def list_reports(self, limit: int = 20) -> list[IntelligenceReport]:
        """List recent reports."""
        return self._reports[-limit:]

    def reset(self) -> None:
        """Reset the intelligence hub."""
        self._signals.clear()
        self._reports.clear()
        self._signal_correlations.clear()
        self._stats = HubStats()
        logger.info("Platform intelligence hub reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class IntelligenceHubConfig:
    """Configuration for the intelligence hub."""
    max_signals: int = 10000
    max_reports: int = 100
    auto_correlate: bool = True
    correlation_threshold: float = 0.5
    pattern_min_occurrences: int = 3
    report_auto_interval_hours: int = 24
    collect_metrics: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_intelligence_hub: PlatformIntelligenceHub | None = None


def get_intelligence_hub() -> PlatformIntelligenceHub:
    """Get or create the singleton intelligence hub."""
    global _intelligence_hub
    if _intelligence_hub is None:
        _intelligence_hub = PlatformIntelligenceHub()
    return _intelligence_hub


def reset_intelligence_hub() -> None:
    """Reset the singleton intelligence hub."""
    global _intelligence_hub
    if _intelligence_hub:
        _intelligence_hub.reset()
    _intelligence_hub = None