from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Sequence

from .benchmark import BenchmarkCase, load_corpus
from .quality import QualityEvidence

QUALITY_SUITE_VERSION = "ourtts-quality-v1"
VALID_TASKS = {"general", "cloning", "expressive", "long_form"}


@dataclass(frozen=True, slots=True)
class TranscriptScore:
    reference: str
    hypothesis: str
    normalized_reference: str
    normalized_hypothesis: str
    reference_words: int
    word_errors: int
    wer: float
    reference_characters: int
    character_errors: int
    cer: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QualitySample:
    engine: str
    case_key: str
    language: str
    task: str
    reference_text: str
    status: str
    evidence_ref: str
    hypothesis_text: str | None = None
    audio_path: str | None = None
    audio_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.engine.strip():
            raise ValueError("quality sample engine must not be empty")
        if not self.case_key.strip():
            raise ValueError("quality sample case_key must not be empty")
        if not self.language.strip():
            raise ValueError("quality sample language must not be empty")
        if self.task not in VALID_TASKS:
            raise ValueError(f"unknown quality task: {self.task!r}")
        if not self.reference_text.strip():
            raise ValueError("quality sample reference_text must not be empty")
        if not self.status.strip():
            raise ValueError("quality sample status must not be empty")
        if not self.evidence_ref.strip():
            raise ValueError("quality sample evidence_ref must not be empty")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "QualitySample":
        return cls(
            engine=str(raw["engine"]),
            case_key=str(raw["case_key"]),
            language=str(raw["language"]),
            task=str(raw.get("task", "general")),
            reference_text=str(raw["reference_text"]),
            status=str(raw["status"]),
            evidence_ref=str(raw["evidence_ref"]),
            hypothesis_text=(
                str(raw["hypothesis_text"]) if raw.get("hypothesis_text") is not None else None
            ),
            audio_path=str(raw["audio_path"]) if raw.get("audio_path") is not None else None,
            audio_sha256=(
                str(raw["audio_sha256"]) if raw.get("audio_sha256") is not None else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ObjectiveSummary:
    engine: str
    language: str
    task: str
    samples: int
    evaluated_transcripts: int
    failures: int
    failure_rate: float
    reference_words: int
    word_errors: int
    wer: float | None
    reference_characters: int
    character_errors: int
    cer: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ListeningRating:
    blind_id: str
    naturalness_mos: float

    def __post_init__(self) -> None:
        if not self.blind_id.strip():
            raise ValueError("rating blind_id must not be empty")
        if not 1.0 <= self.naturalness_mos <= 5.0:
            raise ValueError("naturalness_mos must be between 1 and 5")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ListeningRating":
        return cls(blind_id=str(raw["blind_id"]), naturalness_mos=float(raw["naturalness_mos"]))


def normalize_transcript(text: str) -> str:
    """Deterministic evaluator normalization, intentionally smaller than a language G2P frontend."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    chars: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category.startswith("P"):
            chars.append(" ")
        else:
            chars.append(char)
    return " ".join("".join(chars).split())


def _edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_item in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_item in enumerate(hypothesis, start=1):
            substitution = previous[hyp_index - 1] + (ref_item != hyp_item)
            deletion = previous[hyp_index] + 1
            insertion = current[hyp_index - 1] + 1
            current.append(min(substitution, deletion, insertion))
        previous = current
    return previous[-1]


def _error_rate(errors: int, reference_units: int) -> float:
    if reference_units == 0:
        return 0.0 if errors == 0 else float(errors)
    return errors / reference_units


def score_transcript(reference: str, hypothesis: str) -> TranscriptScore:
    normalized_reference = normalize_transcript(reference)
    normalized_hypothesis = normalize_transcript(hypothesis)
    reference_words = normalized_reference.split()
    hypothesis_words = normalized_hypothesis.split()
    reference_chars = list(normalized_reference.replace(" ", ""))
    hypothesis_chars = list(normalized_hypothesis.replace(" ", ""))
    word_errors = _edit_distance(reference_words, hypothesis_words)
    character_errors = _edit_distance(reference_chars, hypothesis_chars)
    return TranscriptScore(
        reference=reference,
        hypothesis=hypothesis,
        normalized_reference=normalized_reference,
        normalized_hypothesis=normalized_hypothesis,
        reference_words=len(reference_words),
        word_errors=word_errors,
        wer=_error_rate(word_errors, len(reference_words)),
        reference_characters=len(reference_chars),
        character_errors=character_errors,
        cer=_error_rate(character_errors, len(reference_chars)),
    )


def task_for_case(case: BenchmarkCase) -> str:
    tags = set(case.tags)
    if "voice_cloning" in tags:
        return "cloning"
    if "long_form" in tags:
        return "long_form"
    if tags.intersection({"emotion", "prosody", "dialogue"}):
        return "expressive"
    return "general"


def quality_cases(
    *,
    language: str | None = None,
    task: str | None = None,
    corpus_path: Path | None = None,
) -> tuple[BenchmarkCase, ...]:
    if task is not None and task not in VALID_TASKS:
        raise ValueError(f"unknown quality task: {task!r}")
    cases = []
    for case in load_corpus(corpus_path):
        case_task = task_for_case(case)
        if language is not None and case.language != language:
            continue
        if task is not None and case_task != task:
            continue
        cases.append(case)
    return tuple(cases)


def aggregate_objective(samples: Iterable[QualitySample]) -> tuple[ObjectiveSummary, ...]:
    grouped: dict[tuple[str, str, str], list[QualitySample]] = {}
    for sample in samples:
        grouped.setdefault((sample.engine, sample.language, sample.task), []).append(sample)

    summaries: list[ObjectiveSummary] = []
    for (engine, language, task), group in sorted(grouped.items()):
        failures = sum(sample.status != "passed" for sample in group)
        word_errors = 0
        reference_words = 0
        character_errors = 0
        reference_characters = 0
        evaluated = 0
        for sample in group:
            if sample.status != "passed" or sample.hypothesis_text is None:
                continue
            score = score_transcript(sample.reference_text, sample.hypothesis_text)
            word_errors += score.word_errors
            reference_words += score.reference_words
            character_errors += score.character_errors
            reference_characters += score.reference_characters
            evaluated += 1
        summaries.append(
            ObjectiveSummary(
                engine=engine,
                language=language,
                task=task,
                samples=len(group),
                evaluated_transcripts=evaluated,
                failures=failures,
                failure_rate=failures / len(group),
                reference_words=reference_words,
                word_errors=word_errors,
                wer=(
                    _error_rate(word_errors, reference_words) if evaluated and reference_words else None
                ),
                reference_characters=reference_characters,
                character_errors=character_errors,
                cer=(
                    _error_rate(character_errors, reference_characters)
                    if evaluated and reference_characters
                    else None
                ),
            )
        )
    return tuple(summaries)


def _blind_key(sample: QualitySample, seed: str) -> str:
    payload = f"{seed}\0{sample.engine}\0{sample.case_key}\0{sample.audio_sha256 or sample.audio_path or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12].upper()


def build_listening_packet(
    samples: Iterable[QualitySample],
    *,
    seed: str = QUALITY_SUITE_VERSION,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = [
        sample
        for sample in samples
        if sample.status == "passed" and sample.audio_path and sample.reference_text
    ]
    candidates.sort(key=lambda sample: _blind_key(sample, seed))

    public_samples: list[dict[str, Any]] = []
    private_mapping: dict[str, Any] = {}
    for sample in candidates:
        blind_id = f"Q-{_blind_key(sample, seed)}"
        public_samples.append(
            {
                "blind_id": blind_id,
                "case_key": sample.case_key,
                "language": sample.language,
                "task": sample.task,
                "reference_text": sample.reference_text,
                "audio_path": sample.audio_path,
                "rating": {"naturalness_mos": None},
            }
        )
        private_mapping[blind_id] = {
            "engine": sample.engine,
            "case_key": sample.case_key,
            "audio_sha256": sample.audio_sha256,
            "evidence_ref": sample.evidence_ref,
        }

    return (
        {
            "schema_version": 1,
            "suite_version": QUALITY_SUITE_VERSION,
            "blinded": True,
            "samples": public_samples,
        },
        {
            "schema_version": 1,
            "suite_version": QUALITY_SUITE_VERSION,
            "mapping": private_mapping,
        },
    )


def build_release_evidence(
    samples: Iterable[QualitySample],
    ratings: Iterable[ListeningRating],
    mapping: dict[str, Any],
    *,
    evidence_ref: str,
    minimum_samples: int = 10,
    suite_version: str = QUALITY_SUITE_VERSION,
) -> tuple[QualityEvidence, ...]:
    if minimum_samples < 1:
        raise ValueError("minimum_samples must be positive")
    sample_list = tuple(samples)
    summaries = {
        (item.engine, item.language, item.task): item for item in aggregate_objective(sample_list)
    }
    sample_by_identity = {
        (sample.engine, sample.case_key): sample
        for sample in sample_list
        if sample.status == "passed" and sample.hypothesis_text is not None
    }

    mos_by_group: dict[tuple[str, str, str], list[float]] = {}
    seen_blind_ids: set[str] = set()
    private = mapping.get("mapping", mapping)
    for rating in ratings:
        if rating.blind_id in seen_blind_ids:
            raise ValueError(f"duplicate listening rating for {rating.blind_id}")
        seen_blind_ids.add(rating.blind_id)
        identity = private.get(rating.blind_id)
        if not isinstance(identity, dict):
            raise ValueError(f"rating {rating.blind_id!r} has no private engine mapping")
        key = (str(identity["engine"]), str(identity["case_key"]))
        sample = sample_by_identity.get(key)
        if sample is None:
            raise ValueError(f"rating {rating.blind_id!r} does not map to an evaluated sample")
        group = (sample.engine, sample.language, sample.task)
        mos_by_group.setdefault(group, []).append(rating.naturalness_mos)

    evidence: list[QualityEvidence] = []
    for group, scores in sorted(mos_by_group.items()):
        summary = summaries.get(group)
        if summary is None or summary.wer is None:
            continue
        if summary.evaluated_transcripts < minimum_samples or len(scores) < minimum_samples:
            continue
        evidence.append(
            QualityEvidence(
                engine=group[0],
                language=group[1],
                task=group[2],
                samples=min(summary.evaluated_transcripts, len(scores)),
                naturalness_mos=fmean(scores),
                wer=summary.wer,
                failure_rate=summary.failure_rate,
                suite_version=suite_version,
                evidence_ref=evidence_ref,
            )
        )
    return tuple(evidence)


def load_samples(path: Path) -> tuple[QualitySample, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("samples", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("quality samples JSON must contain a list or a {samples: [...]} object")
    return tuple(QualitySample.from_dict(item) for item in items)


def load_ratings(path: Path) -> tuple[ListeningRating, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("ratings", raw.get("samples", raw)) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("ratings JSON must contain a list")
    normalized: list[ListeningRating] = []
    for item in items:
        if "naturalness_mos" not in item and isinstance(item.get("rating"), dict):
            item = {"blind_id": item["blind_id"], "naturalness_mos": item["rating"].get("naturalness_mos")}
        if item.get("naturalness_mos") is None:
            continue
        normalized.append(ListeningRating.from_dict(item))
    return tuple(normalized)


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
