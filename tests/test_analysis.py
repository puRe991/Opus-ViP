import pytest

from opus_vip.analysis import parse_transcript, rank_clips


def test_parse_timestamped_transcript():
    segments = parse_transcript("00:00-00:10 Why does this fail?\n10 --> 20 Here is the solution")
    assert segments[0].start == 0
    assert segments[1].end == 20


def test_rank_clips_prioritizes_hooks_and_questions():
    segments = parse_transcript("""
00:00-00:12 Why do AI tools fail creators?
00:12-00:25 The secret framework starts with a clear problem.
00:25-00:40 Follow this workflow to save editing time.
00:40-00:55 This neutral section has ordinary context.
""")
    clips = rank_clips(segments, target_duration=30, max_clips=3)
    assert clips
    assert clips[0].score >= clips[-1].score
    assert "Why" in clips[0].hook or "secret" in clips[0].hook.lower()


def test_empty_transcript_raises_helpful_error():
    with pytest.raises(ValueError, match="at least one"):
        parse_transcript("\n\n")
