"""Tree-sitter based symbol extraction for Python, JavaScript, TypeScript."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser

from repomemory.models.db import get_session
from repomemory.models.tables import File, Symbol

logger = logging.getLogger(__name__)

# Build language objects
PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())

LANGUAGE_MAP: dict[str, Language] = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".jsx": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TSX_LANGUAGE,
}

# Node types per language that represent extractable symbols
PYTHON_SYMBOL_TYPES = {
    "function_definition": "function",
    "class_definition": "class",
    "import_statement": "import",
    "import_from_statement": "import",
}

JS_TS_SYMBOL_TYPES = {
    "function_declaration": "function",
    "class_declaration": "class",
    "method_definition": "method",
    "arrow_function": "function",
    "import_statement": "import",
    "export_statement": "export",
}


@dataclass
class ExtractedSymbol:
    name: str
    kind: str  # function, class, method, import
    start_line: int
    end_line: int
    signature: str | None = None
    children: list["ExtractedSymbol"] = field(default_factory=list)


def _get_node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _extract_python_symbols(root_node, source_bytes: bytes) -> list[ExtractedSymbol]:
    symbols: list[ExtractedSymbol] = []

    for node in root_node.children:
        node_type = node.type

        if node_type == "function_definition":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
            sig = _get_node_text(params_node, source_bytes) if params_node else ""
            symbols.append(
                ExtractedSymbol(
                    name=name,
                    kind="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=f"def {name}{sig}",
                )
            )

        elif node_type == "class_definition":
            name_node = node.child_by_field_name("name")
            name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
            cls_symbol = ExtractedSymbol(
                name=name,
                kind="class",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                signature=f"class {name}",
            )
            # Extract methods inside class
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        m_name_node = child.child_by_field_name("name")
                        m_params_node = child.child_by_field_name("parameters")
                        m_name = _get_node_text(m_name_node, source_bytes) if m_name_node else "<method>"
                        m_sig = _get_node_text(m_params_node, source_bytes) if m_params_node else ""
                        cls_symbol.children.append(
                            ExtractedSymbol(
                                name=m_name,
                                kind="method",
                                start_line=child.start_point[0] + 1,
                                end_line=child.end_point[0] + 1,
                                signature=f"def {m_name}{m_sig}",
                            )
                        )
            symbols.append(cls_symbol)

        elif node_type in ("import_statement", "import_from_statement"):
            text = _get_node_text(node, source_bytes)
            symbols.append(
                ExtractedSymbol(
                    name=text.strip(),
                    kind="import",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )

        elif node_type == "decorated_definition":
            # Handle decorated functions/classes
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    sub = _extract_python_symbols(type("FakeNode", (), {"children": [child]})(), source_bytes)
                    symbols.extend(sub)

    return symbols


def _extract_js_ts_symbols(root_node, source_bytes: bytes) -> list[ExtractedSymbol]:
    symbols: list[ExtractedSymbol] = []

    def _walk(node):
        for child in node.children:
            ntype = child.type

            if ntype == "function_declaration":
                name_node = child.child_by_field_name("name")
                params_node = child.child_by_field_name("parameters")
                name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
                sig = _get_node_text(params_node, source_bytes) if params_node else ""
                symbols.append(
                    ExtractedSymbol(
                        name=name,
                        kind="function",
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=f"function {name}{sig}",
                    )
                )

            elif ntype == "class_declaration":
                name_node = child.child_by_field_name("name")
                name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
                cls_symbol = ExtractedSymbol(
                    name=name,
                    kind="class",
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    signature=f"class {name}",
                )
                body = child.child_by_field_name("body")
                if body:
                    for member in body.children:
                        if member.type == "method_definition":
                            m_name_node = member.child_by_field_name("name")
                            m_params_node = member.child_by_field_name("parameters")
                            m_name = _get_node_text(m_name_node, source_bytes) if m_name_node else "<method>"
                            m_sig = _get_node_text(m_params_node, source_bytes) if m_params_node else ""
                            cls_symbol.children.append(
                                ExtractedSymbol(
                                    name=m_name,
                                    kind="method",
                                    start_line=member.start_point[0] + 1,
                                    end_line=member.end_point[0] + 1,
                                    signature=f"{m_name}{m_sig}",
                                )
                            )
                symbols.append(cls_symbol)

            elif ntype == "import_statement":
                text = _get_node_text(child, source_bytes)
                symbols.append(
                    ExtractedSymbol(
                        name=text.strip(),
                        kind="import",
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                    )
                )

            elif ntype == "export_statement":
                # Recurse into export to find declarations
                _walk(child)

            elif ntype == "lexical_declaration":
                # const/let/var — check for arrow functions
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        name_node = decl.child_by_field_name("name")
                        value_node = decl.child_by_field_name("value")
                        if value_node and value_node.type == "arrow_function":
                            name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
                            params_node = value_node.child_by_field_name("parameters")
                            sig = _get_node_text(params_node, source_bytes) if params_node else ""
                            symbols.append(
                                ExtractedSymbol(
                                    name=name,
                                    kind="function",
                                    start_line=child.start_point[0] + 1,
                                    end_line=child.end_point[0] + 1,
                                    signature=f"const {name} = {sig} =>",
                                )
                            )

    _walk(root_node)
    return symbols


def extract_symbols_from_file(
    filepath: Path,
    extension: str,
) -> list[ExtractedSymbol]:
    """Parse a file with tree-sitter and extract symbols."""
    language = LANGUAGE_MAP.get(extension)
    if not language:
        return []

    try:
        source_bytes = filepath.read_bytes()
    except OSError:
        logger.warning("Cannot read file: %s", filepath)
        return []

    parser = Parser(language)
    try:
        tree = parser.parse(source_bytes)
    except Exception:
        logger.warning("Tree-sitter parse error for %s", filepath)
        return []

    if extension == ".py":
        return _extract_python_symbols(tree.root_node, source_bytes)
    else:
        return _extract_js_ts_symbols(tree.root_node, source_bytes)


def extract_and_store_symbols(
    repo_root: Path,
    db_files: list[File],
) -> int:
    """Extract symbols from all files and store in DB. Returns total symbol count."""
    total = 0

    with get_session() as session:
        for db_file in db_files:
            filepath = repo_root / db_file.path
            symbols = extract_symbols_from_file(filepath, db_file.extension)

            # Delete old symbols for this file
            session.query(Symbol).filter(Symbol.file_id == db_file.id).delete()

            for sym in symbols:
                db_sym = Symbol(
                    file_id=db_file.id,
                    name=sym.name,
                    kind=sym.kind,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    signature=sym.signature,
                )
                session.add(db_sym)
                session.flush()  # get id for parent reference
                total += 1

                for child in sym.children:
                    db_child = Symbol(
                        file_id=db_file.id,
                        name=child.name,
                        kind=child.kind,
                        start_line=child.start_line,
                        end_line=child.end_line,
                        signature=child.signature,
                        parent_symbol_id=db_sym.id,
                    )
                    session.add(db_child)
                    total += 1

        session.commit()

    logger.info("Extracted %d symbols", total)
    return total
