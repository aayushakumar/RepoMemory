"""RepoMemory CLI — index any repo and search with natural language."""

import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _init():
    """Initialize DB and directories."""
    from repomemory.config import settings
    from repomemory.models.db import init_db

    settings.ensure_dirs()
    init_db()


@click.group()
@click.version_option(package_name="repomemory")
def main():
    """RepoMemory — AI-powered code retrieval engine.

    Index any GitHub repository by URL and search with natural language.
    """
    pass


@main.command()
@click.argument("source")
@click.option("--branch", "-b", default=None, help="Branch or tag to clone (default: repo default)")
@click.option("--token", "-t", default=None, help="GitHub token for private repositories")
def index(source: str, branch: str | None, token: str | None):
    """Index a repository from a URL or local path.

    SOURCE can be a GitHub URL (https://github.com/owner/repo) or a local path.
    """
    _init()

    from pathlib import Path

    from repomemory.indexer.cloner import clone_repo, extract_repo_name, is_git_url
    from repomemory.indexer.orchestrator import index_repository
    from repomemory.models.db import get_session
    from repomemory.models.tables import Repository

    if is_git_url(source):
        repo_name = extract_repo_name(source)
        console.print(f"[cyan]Cloning[/cyan] {repo_name} from {source}...")

        with get_session() as session:
            existing = session.query(Repository).filter(Repository.url == source).first()
            if existing:
                console.print(f"[yellow]Repository already indexed (id={existing.id})[/yellow]")
                return

            repo = Repository(path=source, name=repo_name, url=source, branch=branch, status="indexing")
            session.add(repo)
            session.commit()
            session.refresh(repo)
            repo_id = repo.id

        try:
            clone_path = clone_repo(source, repo_id, branch=branch, token=token)
            with get_session() as session:
                repo = session.get(Repository, repo_id)
                repo.clone_path = str(clone_path)
                session.commit()
        except Exception as e:
            console.print(f"[red]Clone failed:[/red] {e}")
            with get_session() as session:
                repo = session.get(Repository, repo_id)
                if repo:
                    repo.status = "error"
                    repo.error_message = str(e)[:500]
                    session.commit()
            sys.exit(1)

        repo_path = str(clone_path)
    else:
        local_path = Path(source).resolve()
        if not local_path.is_dir():
            console.print(f"[red]Directory not found:[/red] {source}")
            sys.exit(1)

        repo_name = local_path.name
        repo_path = str(local_path)

        with get_session() as session:
            existing = session.query(Repository).filter(Repository.path == repo_path).first()
            if existing:
                console.print(f"[yellow]Repository already indexed (id={existing.id})[/yellow]")
                return

            repo = Repository(path=repo_path, name=repo_name, status="indexing")
            session.add(repo)
            session.commit()
            session.refresh(repo)
            repo_id = repo.id

    console.print(f"[cyan]Indexing[/cyan] {repo_name}...")

    with console.status("[bold green]Running indexing pipeline..."):
        stats = index_repository(repo_id, repo_path)

    console.print("\n[green]✓ Indexed successfully![/green]")
    console.print(f"  Files: {stats.files_indexed}")
    console.print(f"  Symbols: {stats.symbols_extracted}")
    console.print(f"  Chunks: {stats.chunks_created}")
    console.print(f"  Embeddings: {stats.embeddings_generated}")
    console.print(f"  Duration: {stats.duration_seconds:.1f}s")


@main.command()
@click.argument("query")
@click.option("--repo", "-r", default=None, help="Repository name or ID to search")
@click.option("--mode", "-m", default=None, help="Search mode: bug_fix, trace_flow, test_lookup, config_lookup")
@click.option("--top-k", "-k", default=10, help="Number of results to return")
@click.option("--budget", default=8000, help="Token budget for context pack")
def search(query: str, repo: str | None, mode: str | None, top_k: int, budget: int):
    """Search indexed repositories with natural language queries."""
    _init()

    from repomemory.context.packer import build_context_pack
    from repomemory.models.db import get_session
    from repomemory.models.tables import Repository
    from repomemory.retrieval.orchestrator import retrieve

    with get_session() as session:
        if repo:
            # Try as ID first, then name
            try:
                repo_obj = session.get(Repository, int(repo))
            except ValueError:
                repo_obj = session.query(Repository).filter(Repository.name == repo).first()
        else:
            repo_obj = session.query(Repository).filter(Repository.status == "ready").first()

        if not repo_obj:
            console.print("[red]No ready repository found.[/red] Index one first with: repomemory index <url>")
            sys.exit(1)

        if repo_obj.status != "ready":
            console.print(f"[yellow]Repository '{repo_obj.name}' is not ready (status: {repo_obj.status})[/yellow]")
            sys.exit(1)

        repo_id = repo_obj.id
        repo_name = repo_obj.name

    console.print(f"[cyan]Searching[/cyan] '{query}' in [bold]{repo_name}[/bold]...")

    result = retrieve(query=query, repo_id=repo_id, mode=mode, top_k=top_k)
    context = build_context_pack(
        ranked_results=result.ranked_results,
        query=query,
        mode=result.classified_mode,
        budget=budget,
    )

    console.print(f"\nMode: [bold]{result.classified_mode}[/bold]  |  Results: {len(result.ranked_results)}")
    console.print()

    # Results table
    table = Table(title="Search Results", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right", width=7)
    table.add_column("Explanation")

    for i, r in enumerate(result.ranked_results[:top_k], 1):
        table.add_row(str(i), r.file_path, f"{r.combined_score:.3f}", r.explanation)

    console.print(table)

    # Context summary
    pct = f"{context.budget_used_pct:.0f}%"
    console.print(f"\n[dim]Context pack: {context.total_tokens} tokens ({pct} of {budget} budget)[/dim]")


@main.command("list")
def list_repos():
    """List all indexed repositories."""
    _init()

    from repomemory.models.db import get_session
    from repomemory.models.tables import Repository

    with get_session() as session:
        repos = session.query(Repository).all()

    if not repos:
        console.print("[dim]No repositories indexed yet.[/dim]")
        console.print("Run: repomemory index https://github.com/owner/repo")
        return

    table = Table(title="Indexed Repositories")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Name", style="cyan bold")
    table.add_column("Status", width=10)
    table.add_column("Files", justify="right", width=6)
    table.add_column("Symbols", justify="right", width=8)
    table.add_column("Chunks", justify="right", width=7)
    table.add_column("Source")

    for r in repos:
        status_style = {"ready": "green", "indexing": "yellow", "error": "red"}.get(r.status, "dim")
        source = r.url or r.path
        if len(source) > 50:
            source = "..." + source[-47:]
        table.add_row(
            str(r.id),
            r.name,
            f"[{status_style}]{r.status}[/{status_style}]",
            str(r.file_count),
            str(r.symbol_count),
            str(r.chunk_count),
            source,
        )

    console.print(table)


@main.command()
@click.argument("repo_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete(repo_id: int, yes: bool):
    """Delete an indexed repository."""
    _init()

    from repomemory.indexer.cloner import delete_clone
    from repomemory.models.db import get_session
    from repomemory.models.tables import Repository

    with get_session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            console.print(f"[red]Repository {repo_id} not found[/red]")
            sys.exit(1)

        if not yes:
            if not click.confirm(f"Delete '{repo.name}' (id={repo_id})?"):
                return

        if repo.url:
            delete_clone(repo_id)

        session.delete(repo)
        session.commit()

    console.print(f"[green]✓ Deleted repository {repo_id}[/green]")


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the RepoMemory web server."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed.[/red] Install with: pip install repomemory[server]")
        sys.exit(1)

    console.print(f"[cyan]Starting RepoMemory server[/cyan] on {host}:{port}")
    uvicorn.run("repomemory.api.app:app", host=host, port=port, reload=reload)


@main.command()
def config():
    """Show current configuration."""
    from repomemory.config import settings

    table = Table(title="RepoMemory Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Data directory", str(settings.data_dir))
    table.add_row("Database", str(settings.get_db_path()))
    table.add_row("FAISS index dir", str(settings.get_faiss_index_dir()))
    table.add_row("Clone directory", str(settings.get_clone_dir()))
    table.add_row("Embedding provider", settings.embedding_provider)
    table.add_row("Embedding model", settings.embedding_model)
    table.add_row("LLM enabled", "✓" if settings.llm_enabled else "✗")
    table.add_row("Groq model", settings.groq_model if settings.llm_enabled else "[dim]n/a[/dim]")
    table.add_row("HF API key", "✓ set" if settings.hf_api_key else "[dim]not set[/dim]")
    table.add_row("Max file size", f"{settings.max_file_size_kb} KB")
    table.add_row("Max clone size", f"{settings.max_clone_size_mb} MB")
    table.add_row("Token budget", str(settings.token_budget))

    console.print(table)


if __name__ == "__main__":
    main()
