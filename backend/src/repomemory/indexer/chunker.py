"""Content chunking — symbol-aware + sliding window fallback."""

import logging
from pathlib import Path

import tiktoken

from repomemory.config import settings
from repomemory.models.db import get_session
from repomemory.models.tables import Chunk, File, Symbol

logger = logging.getLogger(__name__)

_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def count_tokens(text: str) -> int:
    return len(_get_tokenizer().encode(text, disallowed_special=()))


def _read_file_lines(filepath: Path) -> list[str] | None:
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except OSError:
        return None


def _make_chunks_from_symbols(
    lines: list[str],
    symbols: list[Symbol],
    file_id: int,
    max_tokens: int,
) -> list[dict]:
    """Create chunks from symbol boundaries."""
    chunks = []
    covered_lines: set[int] = set()

    for sym in symbols:
        if sym.kind == "import":
            continue  # skip import lines as standalone chunks

        start = sym.start_line - 1  # 0-indexed
        end = sym.end_line  # exclusive
        content = "".join(lines[start:end])
        tokens = count_tokens(content)

        if tokens > max_tokens:
            # Split large symbol into sub-chunks
            sub_chunks = _sliding_window_chunk(
                lines[start:end],
                file_id,
                sym.id,
                offset=start,
                window_size=settings.sliding_window_lines,
                overlap=settings.sliding_window_overlap,
                max_tokens=max_tokens,
            )
            chunks.extend(sub_chunks)
        else:
            chunks.append(
                {
                    "file_id": file_id,
                    "symbol_id": sym.id,
                    "content": content,
                    "start_line": sym.start_line,
                    "end_line": sym.end_line,
                    "token_count": tokens,
                }
            )

        for i in range(start, end):
            covered_lines.add(i)

    return chunks, covered_lines


def _sliding_window_chunk(
    lines: list[str],
    file_id: int,
    symbol_id: int | None,
    offset: int = 0,
    window_size: int = 200,
    overlap: int = 50,
    max_tokens: int = 512,
) -> list[dict]:
    """Chunk lines using a sliding window."""
    chunks = []
    i = 0
    total = len(lines)

    while i < total:
        end = min(i + window_size, total)
        content = "".join(lines[i:end])
        tokens = count_tokens(content)

        # If still over budget, shrink window
        while tokens > max_tokens and end > i + 1:
            end -= 10
            content = "".join(lines[i:end])
            tokens = count_tokens(content)

        chunks.append(
            {
                "file_id": file_id,
                "symbol_id": symbol_id,
                "content": content,
                "start_line": offset + i + 1,
                "end_line": offset + end,
                "token_count": tokens,
            }
        )

        step = max(end - i - overlap, 1)
        i += step

    return chunks


def chunk_file(
    filepath: Path,
    db_file: File,
    symbols: list[Symbol],
) -> list[dict]:
    """Chunk a single file. Returns list of chunk dicts."""
    lines = _read_file_lines(filepath)
    if not lines:
        return []

    max_tokens = settings.max_chunk_tokens
    chunks = []

    # Symbol-aware chunking if symbols exist
    non_import_symbols = [s for s in symbols if s.kind != "import"]
    if non_import_symbols:
        sym_chunks, covered = _make_chunks_from_symbols(lines, non_import_symbols, db_file.id, max_tokens)
        chunks.extend(sym_chunks)

        # Chunk uncovered regions
        uncovered_start = None
        for i in range(len(lines)):
            if i not in covered:
                if uncovered_start is None:
                    uncovered_start = i
            else:
                if uncovered_start is not None:
                    region = lines[uncovered_start:i]
                    content = "".join(region)
                    tokens = count_tokens(content)
                    if tokens > 10:  # skip trivial regions
                        if tokens > max_tokens:
                            chunks.extend(
                                _sliding_window_chunk(
                                    region,
                                    db_file.id,
                                    None,
                                    offset=uncovered_start,
                                    max_tokens=max_tokens,
                                )
                            )
                        else:
                            chunks.append(
                                {
                                    "file_id": db_file.id,
                                    "symbol_id": None,
                                    "content": content,
                                    "start_line": uncovered_start + 1,
                                    "end_line": i,
                                    "token_count": tokens,
                                }
                            )
                    uncovered_start = None

        # Handle trailing uncovered
        if uncovered_start is not None:
            region = lines[uncovered_start:]
            content = "".join(region)
            tokens = count_tokens(content)
            if tokens > 10:
                if tokens > max_tokens:
                    chunks.extend(
                        _sliding_window_chunk(
                            region,
                            db_file.id,
                            None,
                            offset=uncovered_start,
                            max_tokens=max_tokens,
                        )
                    )
                else:
                    chunks.append(
                        {
                            "file_id": db_file.id,
                            "symbol_id": None,
                            "content": content,
                            "start_line": uncovered_start + 1,
                            "end_line": len(lines),
                            "token_count": tokens,
                        }
                    )
    else:
        # No symbols — full sliding window
        chunks.extend(
            _sliding_window_chunk(
                lines,
                db_file.id,
                None,
                max_tokens=max_tokens,
            )
        )

    return chunks


def chunk_and_store(
    repo_root: Path,
    db_files: list[File],
) -> int:
    """Chunk all files and store in DB. Returns total chunk count."""
    total = 0

    with get_session() as session:
        for db_file in db_files:
            filepath = repo_root / db_file.path

            # Get symbols for this file
            symbols = session.query(Symbol).filter(Symbol.file_id == db_file.id).all()

            # Delete old chunks
            session.query(Chunk).filter(Chunk.file_id == db_file.id).delete()

            chunks = chunk_file(filepath, db_file, symbols)

            for c in chunks:
                db_chunk = Chunk(
                    file_id=c["file_id"],
                    symbol_id=c["symbol_id"],
                    content=c["content"],
                    start_line=c["start_line"],
                    end_line=c["end_line"],
                    token_count=c["token_count"],
                )
                session.add(db_chunk)
                total += 1

        session.commit()

    logger.info("Created %d chunks", total)
    return total
