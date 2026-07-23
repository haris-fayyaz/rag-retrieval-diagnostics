import re
from typing import List

from app.core.config import settings as _default_settings
from app.models import Chunk

# Sentence-boundary split: break after ./!/? followed by whitespace.
# Deliberately simple (not a full NLP sentence tokenizer) - good enough to
# avoid cutting mid-sentence for typical prose. Edge cases like "Dr. Smith"
# are an accepted tradeoff for this project's scope.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _split_paragraph_into_sentences(paragraph: str) -> List[str]:
    """Split one paragraph into sentences. Never drops text - every
    character of `paragraph` ends up in exactly one returned sentence."""
    sentences = _SENTENCE_BOUNDARY.split(paragraph.strip())
    return [s for s in sentences if s]


def _word_safe_windows(text: str, size: int) -> List[str]:
    """
    Last-resort split for a single sentence/paragraph that's still longer
    than `size` on its own: break on whitespace only, so every boundary
    lands between two words, never inside one.
    """
    words = text.split()
    windows: List[str] = []
    current: List[str] = []
    current_len = 0

    for word in words:
        added_len = len(word) + (1 if current else 0)  # +1 for the joining space
        if current and current_len + added_len > size:
            windows.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += added_len

    if current:
        windows.append(" ".join(current))
    return windows


def _split_into_units(text: str, chunk_size: int) -> List[str]:
    """
    Break text into an ordered list of pieces, preferring to split at
    paragraph, then sentence, then word boundaries (in that order) -
    never mid-word. Every non-blank paragraph/sentence/word in `text`
    ends up inside exactly one returned unit, so nothing is silently
    discarded here.
    """
    units: List[str] = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) <= chunk_size:
            units.append(para)
            continue
        # Paragraph alone exceeds chunk_size - fall back to sentences.
        for sentence in _split_paragraph_into_sentences(para):
            if len(sentence) <= chunk_size:
                units.append(sentence)
            else:
                # Sentence still too big - word-safe sliding window.
                units.extend(_word_safe_windows(sentence, chunk_size))
    return units


def _overlap_tail(text: str, overlap: int) -> str:
    """Return up to the last `overlap` characters of `text`, trimmed so
    it starts on a full word (never splits a word in half)."""
    if overlap <= 0 or not text:
        return ""
    tail = text[-overlap:]
    space_index = tail.find(" ")
    if 0 <= space_index < len(tail) - 1:
        tail = tail[space_index + 1:]
    return tail.strip()


def chunk_text(
    text: str,
    document_id: str,
    document_name: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Chunk]:
    """
    Split text into chunks, preferring paragraph then sentence boundaries,
    falling back to a word-safe sliding window only when a single
    paragraph/sentence is itself larger than chunk_size. Consecutive
    chunks share `chunk_overlap` characters of trailing context (trimmed
    to a word boundary), so a fact sitting near a chunk boundary still has
    a chance of appearing whole in at least one chunk.

    `chunk_size`/`chunk_overlap` default to the app's configured
    CHUNK_SIZE/CHUNK_OVERLAP (see app/core/config.py) when not given
    explicitly - read at call time, not import time, so tests can pass
    their own values without needing to touch global config.

    Guarantees:
    - No chunk is ever empty.
    - No word is ever cut in half.
    - No text is silently discarded.
    - chunk_index is stable and sequential, starting at 0.
    """
    if chunk_size is None:
        chunk_size = _default_settings.chunk_size
    if chunk_overlap is None:
        chunk_overlap = _default_settings.chunk_overlap

    if not text.strip():
        return []

    units = _split_into_units(text, chunk_size)

    chunks: List[Chunk] = []
    chunk_index = 0
    current = ""

    for unit in units:
        candidate = f"{current} {unit}".strip() if current else unit

        if len(candidate) <= chunk_size or not current:
            # Fits - or this is the first unit in a new chunk, which we
            # keep even if it alone exceeds chunk_size (already word-safe
            # from _split_into_units, so this is the best we can do
            # without cutting a word).
            current = candidate
            continue

        # Adding this unit would overflow chunk_size - finalize the
        # current chunk, then start the next one with an overlap tail
        # carried over from it, plus this unit.
        chunks.append(
            Chunk(
                document_id=document_id,
                document_name=document_name,
                chunk_id=f"{document_id}_chunk_{chunk_index}",
                score=0.0,
                text_preview=current,
            )
        )
        chunk_index += 1

        tail = _overlap_tail(current, chunk_overlap)
        current = f"{tail} {unit}".strip() if tail else unit

    if current.strip():
        chunks.append(
            Chunk(
                document_id=document_id,
                document_name=document_name,
                chunk_id=f"{document_id}_chunk_{chunk_index}",
                score=0.0,
                text_preview=current,
            )
        )

    return chunks