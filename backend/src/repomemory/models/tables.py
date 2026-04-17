"""SQLAlchemy ORM table definitions."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from repomemory.models.db import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(256), nullable=True)
    clone_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    language_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, indexing, ready, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_commit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Counts cached for fast lookup
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    files: Mapped[list["File"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    queries: Mapped[list["Query"]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)  # relative to repo root
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    last_modified: Mapped[float] = mapped_column(Float, nullable=False)  # unix timestamp
    git_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256

    repository: Mapped["Repository"] = relationship(back_populates="files")
    symbols: Mapped[list["Symbol"]] = relationship(back_populates="file", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_files_repo_path", "repo_id", "path", unique=True),
        Index("ix_files_content_hash", "content_hash"),
    )


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # function, class, method, import
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_symbol_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True
    )

    file: Mapped["File"] = relationship(back_populates="symbols")
    children: Mapped[list["Symbol"]] = relationship(back_populates="parent", remote_side=[parent_symbol_id])
    parent: Mapped["Symbol | None"] = relationship(back_populates="children", remote_side=[id])

    __table_args__ = (
        Index("ix_symbols_file", "file_id"),
        Index("ix_symbols_name", "name"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    symbol_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    faiss_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # position in FAISS index

    file: Mapped["File"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_file", "file_id"),
        Index("ix_chunks_faiss", "faiss_index"),
    )


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    result_count: Mapped[int] = mapped_column(Integer, default=0)

    repository: Mapped["Repository"] = relationship(back_populates="queries")
    actions: Mapped[list["UserAction"]] = relationship(back_populates="query", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_queries_repo", "repo_id"),)


class UserAction(Base):
    __tablename__ = "user_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # file, symbol, chunk
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # opened, selected, accepted, dismissed, thumbs_up, thumbs_down
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    query: Mapped["Query"] = relationship(back_populates="actions")

    __table_args__ = (
        Index("ix_user_actions_query", "query_id"),
        Index("ix_user_actions_target", "target_type", "target_id"),
    )


def _register_all():
    """Ensure all models are loaded (for create_all)."""
    pass


class DependencyEdge(Base):
    """Import/dependency relationship between files."""

    __tablename__ = "dependency_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    target_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    import_name: Mapped[str] = mapped_column(String(512), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="import")  # import, from_import, require

    __table_args__ = (
        Index("ix_dep_edges_repo", "repo_id"),
        Index("ix_dep_edges_source", "source_file_id"),
        Index("ix_dep_edges_target", "target_file_id"),
    )


class LearnedWeights(Base):
    """Adaptive retrieval weights learned from user feedback."""

    __tablename__ = "learned_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON dict of signal -> weight
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_learned_weights_repo_mode", "repo_id", "mode", unique=True),)
