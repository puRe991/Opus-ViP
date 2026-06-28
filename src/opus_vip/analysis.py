"""Heuristic clip analysis for Opus-ViP.

The module deliberately keeps the first MVP dependency-free. In production this
is the seam for ASR, scene detection, face tracking, and LLM-based hook scoring.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
import re
from typing import Iterable

HOOK_WORDS = {
    "secret", "mistake", "truth", "why", "how", "never", "always", "best",
    "worst", "money", "growth", "viral", "ai", "watch", "stop", "start",
    "problem", "solution", "framework", "hack", "risk", "warning",
}
CTA_WORDS = {"follow", "subscribe", "share", "comment", "save", "download", "try"}
QUESTION_RE = re.compile(r"\?")
WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    def validate(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("segment timestamps must be non-negative and increasing")
        if not self.text.strip():
            raise ValueError("segment text must not be empty")


@dataclass(frozen=True)
class ClipCandidate:
    title: str
    start: float
    end: float
    score: int
    hook: str
    rationale: list[str]
    captions: list[TranscriptSegment]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["duration"] = round(self.end - self.start, 2)
        return data


def parse_transcript(raw: str) -> list[TranscriptSegment]:
    """Parse transcript text into timestamped segments.

    Accepted line formats:
    - ``00:00-00:12 Text``
    - ``12.5 --> 30.0 Text``
    - plain text lines, which receive synthetic 8-second windows
    """
    segments: list[TranscriptSegment] = []
    synthetic_start = 0.0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(?P<a>[\d:.]+)\s*(?:-->|-|–)\s*(?P<b>[\d:.]+)\s+(?P<t>.+)$", line)
        if match:
            start = _parse_time(match.group("a"))
            end = _parse_time(match.group("b"))
            text = match.group("t").strip()
        else:
            words = len(WORD_RE.findall(line))
            duration = max(5.0, min(14.0, words / 2.4))
            start = synthetic_start
            end = synthetic_start + duration
            text = line
            synthetic_start = end
        segment = TranscriptSegment(start=start, end=end, text=text)
        segment.validate()
        segments.append(segment)
    if not segments:
        raise ValueError("transcript must contain at least one non-empty line")
    return segments


def rank_clips(segments: Iterable[TranscriptSegment], target_duration: int = 45, max_clips: int = 8) -> list[ClipCandidate]:
    """Create ranked short-form clip candidates from transcript segments."""
    if target_duration < 15 or target_duration > 180:
        raise ValueError("target_duration must be between 15 and 180 seconds")
    ordered = sorted(segments, key=lambda s: s.start)
    for segment in ordered:
        segment.validate()
    windows: list[list[TranscriptSegment]] = []
    for idx, _ in enumerate(ordered):
        window: list[TranscriptSegment] = []
        for segment in ordered[idx:]:
            if window and segment.end - window[0].start > target_duration * 1.35:
                break
            window.append(segment)
            duration = window[-1].end - window[0].start
            if duration >= target_duration * 0.55:
                windows.append(window.copy())
    if not windows:
        windows = [ordered]

    candidates = [_score_window(window, target_duration) for window in windows]
    deduped: list[ClipCandidate] = []
    for candidate in sorted(candidates, key=lambda c: c.score, reverse=True):
        if all(abs(candidate.start - existing.start) > 10 for existing in deduped):
            deduped.append(candidate)
        if len(deduped) >= max_clips:
            break
    return deduped


def _score_window(window: list[TranscriptSegment], target_duration: int) -> ClipCandidate:
    text = " ".join(segment.text for segment in window)
    words = [word.lower() for word in WORD_RE.findall(text)]
    unique_words = len(set(words))
    hook_hits = sorted(set(words) & HOOK_WORDS)
    cta_hits = sorted(set(words) & CTA_WORDS)
    question_bonus = 10 if QUESTION_RE.search(text) else 0
    density = min(20, ceil(len(words) / max(1, window[-1].end - window[0].start) * 8))
    duration = window[-1].end - window[0].start
    duration_fit = max(0, 20 - int(abs(duration - target_duration) / target_duration * 20))
    novelty = min(15, unique_words // 4)
    score = min(100, 35 + len(hook_hits) * 6 + len(cta_hits) * 3 + question_bonus + density + duration_fit + novelty)
    rationale = []
    if hook_hits:
        rationale.append(f"Hook-Begriffe: {', '.join(hook_hits[:5])}")
    if question_bonus:
        rationale.append("enthält eine direkte Frage")
    rationale.append(f"Dauer passt zu {target_duration}s Ziel")
    if cta_hits:
        rationale.append(f"CTA-Signale: {', '.join(cta_hits[:3])}")
    return ClipCandidate(
        title=_title_from_text(text),
        start=round(window[0].start, 2),
        end=round(window[-1].end, 2),
        score=score,
        hook=window[0].text[:180],
        rationale=rationale,
        captions=window,
    )


def _parse_time(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"invalid timestamp: {value}")


def _title_from_text(text: str) -> str:
    words = WORD_RE.findall(text)
    title = " ".join(words[:9]).strip()
    return title[:72] or "Untitled clip"
