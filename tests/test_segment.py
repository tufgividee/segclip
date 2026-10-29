import pytest

from segclip.segment import format_segments, split_payload


def test_short_text_is_unchanged():
    source = "A short message.\nWith whitespace preserved.\n"

    result = format_segments(source, char_limit=100)

    assert len(result.segments) == 1
    assert result.segments[0].text == source
    assert result.segments[0].payload == source
    assert result.total_clipboard_characters == len(source)


def test_exact_limit_is_unchanged():
    source = "x" * 100

    result = format_segments(source, char_limit=100)

    assert len(result.segments) == 1
    assert result.segments[0].text == source



def test_long_text_is_split_and_reconstructs():
    source = ("line one\nline two\nline three\n" * 20)

    result = format_segments(source, char_limit=40)

    assert len(result.segments) > 1
    assert "".join(segment.payload for segment in result.segments) == source
    assert all(len(segment.payload) <= 40 for segment in result.segments)

    # Every segment has its own start and end markers.
    assert all(
        "<|SEGCLIP_SEGMENT|>" in segment.text
        for segment in result.segments
    )
    assert all(
        "<|SEGCLIP_END_SEGMENT|>" in segment.text
        for segment in result.segments
    )

    # Sequence markers appear only at the sequence boundaries.
    assert "<|SEGCLIP_START|>" in result.segments[0].text
    assert all(
        "<|SEGCLIP_START|>" not in segment.text
        for segment in result.segments[1:]
    )
    assert "<|SEGCLIP_END|>" in result.segments[-1].text
    assert all(
        "<|SEGCLIP_END|>" not in segment.text
        for segment in result.segments[:-1]
    )


def test_last_segment_has_sequence_end_marker():
    result = format_segments("abcdef" * 20, char_limit=30)

    assert len(result.segments) > 1
    assert "<|SEGCLIP_END|>" not in result.segments[0].text
    assert "<|SEGCLIP_END|>" in result.segments[-1].text
    assert "<CONTEXT_CONCLUSION>" not in result.segments[-1].text



def test_total_counts_formatted_messages():
    result = format_segments("abcdef" * 20, char_limit=30)

    assert result.total_clipboard_characters == sum(
        len(segment.text) for segment in result.segments
    )


@pytest.mark.parametrize("limit", [0, -1])
def test_invalid_limit(limit):
    with pytest.raises(ValueError):
        format_segments("hello", char_limit=limit)


def test_split_payload_preserves_marker_like_text():
    source = "alpha\n<SEGMENT_STATUS>\nbeta\n" * 20

    parts = split_payload(source, char_limit=25)

    assert "".join(parts) == source
    assert all(len(part) <= 25 for part in parts)


def test_prefers_line_boundaries():
    source = "first line\nsecond line\nthird line\n"

    parts = split_payload(source, char_limit=23)

    assert parts == ["first line\nsecond line\n", "third line\n"]
    assert "".join(parts) == source


def test_prefers_sentence_boundary_when_no_newline_fits():
    source = "First sentence. Second sentence. Third sentence."

    parts = split_payload(source, char_limit=32)

    assert parts[0] == "First sentence. "
    assert "".join(parts) == source
    assert all(len(part) <= 32 for part in parts)


def test_splits_long_sentence_at_whitespace():
    source = "alpha beta gamma delta epsilon"

    parts = split_payload(source, char_limit=16)

    assert all(len(part) <= 16 for part in parts)
    assert "".join(parts) == source


def test_splits_unbroken_token_as_last_resort():
    source = "x" * 25

    parts = split_payload(source, char_limit=10)

    assert parts == ["x" * 10, "x" * 10, "x" * 5]
    assert "".join(parts) == source
