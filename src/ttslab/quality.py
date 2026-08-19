from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .registry import repository_root


@dataclass(frozen=True, slots=True)
class QualityEvidence:
    """Measured quality evidence for one engine/language/task.

    Values are measurements, never model-card claims. `naturalness_mos` is expected on the
    conventional 1..5 listening-test scale. WER and failure rate are fractions in 0..1.
    """

    engine: str
    language: str
    task: str
    samples: int
    naturalness_mos: float
    wer: float
    failure_rate: float
    suite_version: str
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.engine.strip():
            raise ValueError("quality evidence engine must not be empty")
        if not self.language.strip():
            raise ValueError("quality evidence language must not be empty")
        if self.task not in {"general", "cloning", "expressive", "long_form"}:
            raise ValueError(f"unknown quality task: {self.task!r}")
        if self.samples < 1:
            raise ValueError("quality evidence requires at least one sample")
        if not 1.0 <= self.naturalness_mos <= 5.0:
            raise ValueError("naturalness_mos must be between 1 and 5")
        if not 0.0 <= self.wer <= 1.0:
            raise ValueError("wer must be between 0 and 1")
        if not 0.0 <= self.failure_rate <= 1.0:
            raise ValueError("failure_rate must be between 0 and 1")
        if not self.suite_version.strip():
            raise ValueError("suite_version must not be empty")
        if not self.evidence_ref.strip():
            raise ValueError("evidence_ref must point to retained evidence")

    @property
    def score(self) -> float:
        """Transparent v1 product score; policy weights are not benchmark measurements."""
        naturalness = (self.naturalness_mos - 1.0) / 4.0
        intelligibility = 1.0 - self.wer
        stability = 1.0 - self.failure_rate
        return round(100.0 * (0.55 * naturalness + 0.30 * intelligibility + 0.15 * stability), 4)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["score"] = self.score
        return payload


@dataclass(frozen=True, slots=True)
class QualityLedger:
    schema_version: int
    suite_version: str
    minimum_samples: int
    evidence: tuple[QualityEvidence, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"unsupported quality ledger schema: {self.schema_version}")
        if self.minimum_samples < 1:
            raise ValueError("minimum_samples must be positive")
        for item in self.evidence:
            if item.suite_version != self.suite_version:
                raise ValueError(
                    f"quality evidence suite mismatch for {item.engine}: "
                    f"{item.suite_version!r} != {self.suite_version!r}"
                )

    def ranked(
        self,
        *,
        language: str,
        task: str = "general",
        eligible_engines: set[str] | None = None,
    ) -> tuple[QualityEvidence, ...]:
        requested_language = language.casefold()
        items = [
            item
            for item in self.evidence
            if item.task == task
            and item.samples >= self.minimum_samples
            and item.language.casefold() in {requested_language, "*"}
            and (eligible_engines is None or item.engine in eligible_engines)
        ]
        return tuple(sorted(items, key=lambda item: (-item.score, item.engine)))

    def best(
        self,
        *,
        language: str,
        task: str = "general",
        eligible_engines: set[str] | None = None,
    ) -> QualityEvidence:
        ranked = self.ranked(language=language, task=task, eligible_engines=eligible_engines)
        if not ranked:
            raise ValueError(
                f"No release-quality evidence for task={task!r}, language={language!r}. "
                "Run the common quality suite before using Best."
            )
        return ranked[0]


def default_quality_path() -> Path:
    return repository_root() / "benchmarks" / "quality" / "ledger.json"


def load_quality_ledger(path: Path | None = None) -> QualityLedger:
    ledger_path = path or default_quality_path()
    raw = json.loads(ledger_path.read_text(encoding="utf-8"))
    evidence = tuple(QualityEvidence(**item) for item in raw.get("evidence", []))
    return QualityLedger(
        schema_version=int(raw.get("schema_version", 1)),
        suite_version=str(raw["suite_version"]),
        minimum_samples=int(raw.get("minimum_samples", 10)),
        evidence=evidence,
    )
