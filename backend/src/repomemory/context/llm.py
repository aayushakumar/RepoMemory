"""LLM integration via Groq for AI-powered code explanations."""

import logging

from repomemory.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazily initialize the Groq client."""
    global _client
    if _client is None:
        try:
            from groq import Groq

            _client = Groq(api_key=settings.groq_api_key)
            logger.info("Initialized Groq client (model=%s)", settings.groq_model)
        except ImportError:
            logger.warning("groq package not installed — install with: pip install repomemory[llm]")
            return None
        except Exception as e:
            logger.warning("Failed to initialize Groq client: %s", e)
            return None
    return _client


def explain_code(query: str, code_snippet: str, file_path: str) -> str | None:
    """Generate an AI explanation for why a code snippet is relevant to a query.

    Returns None if LLM is unavailable, allowing fallback to templates.
    """
    if not settings.llm_enabled:
        return None

    client = _get_client()
    if not client:
        return None

    prompt = (
        f"You are a code analysis assistant. Explain in 1-2 sentences why this code "
        f"from `{file_path}` is relevant to the developer's query.\n\n"
        f"Query: {query}\n\n"
        f"Code:\n```\n{code_snippet[:2000]}\n```\n\n"
        f"Explanation (be specific and concise):"
    )

    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Groq API call failed: %s", e)
        return None


def summarize_context(query: str, context_files: list[dict]) -> str | None:
    """Generate an AI summary of how the retrieved context answers the query.

    Returns None if LLM is unavailable.
    """
    if not settings.llm_enabled:
        return None

    client = _get_client()
    if not client:
        return None

    # Build a condensed view of files
    file_summaries = []
    for f in context_files[:10]:
        snippets = f.get("snippets", [])
        snippet_text = snippets[0]["content"][:500] if snippets else ""
        file_summaries.append(f"- `{f['path']}` (score: {f.get('relevance_score', 0):.2f})\n{snippet_text}")

    files_text = "\n\n".join(file_summaries)

    prompt = (
        f"You are a code analysis assistant. A developer searched for: \"{query}\"\n\n"
        f"The following relevant files were found:\n\n{files_text}\n\n"
        f"Provide a concise summary (3-5 sentences) explaining how these files relate "
        f"to the query and what the developer should look at first."
    )

    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Groq API call failed: %s", e)
        return None
