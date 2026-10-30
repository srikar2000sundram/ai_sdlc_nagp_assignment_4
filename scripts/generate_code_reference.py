"""Generate docs/guides/20-code-reference.md from the docstrings and doc comments in the code.

    python scripts/generate_code_reference.py

The reference is built from the source itself (Python docstrings, JSDoc blocks in the web UI and the end-to-end page
objects), so it cannot drift from the code. Rebuild the PDFs afterwards with `python scripts/build_docs.py`.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "guides" / "20-code-reference.md"

# (title, folder, description, detail): "full" lists every class and function; "summary" lists only what each file is for.
PYTHON_GROUPS = [
    ("Domain layer", "backend/src/invoice_app/domain", "Business rules. No web or storage code.", "full"),
    ("API layer", "backend/src/invoice_app/api", "HTTP routers, sign-in, serialization and the in-memory repository.", "full"),
    ("Hooks", ".claude/hooks", "Hooks that log every AI interaction and check outputs.", "full"),
    ("Tests", "backend/tests", "What each test module covers, and the shared fake.", "summary"),
    ("Scripts", "scripts", "Helper scripts for cases, documentation and the demo video.", "summary"),
]


def sections_to_markdown(docstring: str) -> str:
    """Turn a docstring with Args/Returns/Raises/Attributes blocks into Markdown."""
    out, in_block = [], False
    for line in docstring.split("\n"):
        header = re.fullmatch(r"(Args|Returns|Raises|Attributes|Expected):\s*(.*)", line.strip())
        if header and not line.startswith(" "):
            out.append(f"**{header.group(1)}**" + (f" {header.group(2)}" if header.group(2) else ""))
            out.append("")
            in_block = True
        elif in_block and line.startswith("    "):
            out.append("- " + line.strip())
        elif in_block and not line.strip():
            in_block = False
            out.append("")
        else:
            out.append(line)
    text = "\n".join(out).strip()
    # Markdown needs a blank line between a paragraph and a list that follows it.
    return re.sub(r"([^\n-][^\n]*)\n(- )", r"\1\n\n\2", text)


def signature(node: ast.AST) -> str:
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix}{node.name}({ast.unparse(node.args)}){returns}"


def python_module(path: Path, detail: str = "full") -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    relative = path.relative_to(ROOT).as_posix()
    lines = [f"### `{relative}`", ""]
    summary = ast.get_docstring(tree)
    lines += [sections_to_markdown(summary), ""] if summary else ["_No module description._", ""]
    if detail == "summary":
        return "\n".join(lines)

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            bases = ", ".join(ast.unparse(base) for base in node.bases)
            lines += [f"#### class `{node.name}`" + (f" ({bases})" if bases else ""), ""]
            doc = ast.get_docstring(node)
            lines += [sections_to_markdown(doc), ""] if doc else []
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    not member.name.startswith("_") or member.name == "__init__"
                ):
                    lines += [f"**`{member.name}`**", "", "```python", signature(member), "```", ""]
                    member_doc = ast.get_docstring(member)
                    lines += [sections_to_markdown(member_doc), ""] if member_doc else []
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(("_", "test_")):
            lines += [f"#### `{node.name}`", "", "```python", signature(node), "```", ""]
            doc = ast.get_docstring(node)
            lines += [sections_to_markdown(doc), ""] if doc else []
    return "\n".join(lines)


def doc_blocks(source: str, declaration: str) -> list[tuple[str, str]]:
    """Pair each /** ... */ block with the declaration line that follows it."""
    found = []
    for match in re.finditer(r"/\*\*(.*?)\*/\s*\n\s*(" + declaration + r")", source, re.S):
        text = "\n".join(re.sub(r"^\s*\* ?", "", line) for line in match.group(1).strip().split("\n")).strip()
        found.append((match.group(2).strip(), text))
    return found


def javascript_section() -> str:
    path = ROOT / "backend/src/invoice_app/api/wwwroot/app.js"
    source = path.read_text(encoding="utf-8")
    header = re.search(r"/\*\*(.*?)\*/", source, re.S)
    lines = [f"### `{path.relative_to(ROOT).as_posix()}`", ""]
    if header:
        lines += ["\n".join(re.sub(r"^\s*\* ?", "", l) for l in header.group(1).strip().split("\n")).strip(), ""]
    for declaration, text in doc_blocks(source, r"(?:async )?function \w+\([^)]*\)"):
        lines += ["```javascript", declaration, "```", "", text, ""]
    return "\n".join(lines)


def typescript_section(relative: str) -> str:
    path = ROOT / relative
    source = path.read_text(encoding="utf-8")
    lines = [f"### `{relative}`", ""]
    for declaration, text in doc_blocks(source, r"(?:export class \w+|(?:async )?\w+\([^)]*\)(?:: \w+)?)"):
        lines += ["```typescript", declaration, "```", "", text, ""]
    return "\n".join(lines)


def main() -> None:
    parts = [
        "# Code Reference",
        "",
        "Every module, class and function, with its purpose, arguments, return value and errors. **Generated** from the "
        "docstrings and doc comments in the source by `scripts/generate_code_reference.py`; do not edit it by hand. "
        "Private helpers (names starting with an underscore) and individual tests are left out.",
        "",
    ]
    for title, folder, description, detail in PYTHON_GROUPS:
        parts += [f"## {title}", "", description, ""]
        for path in sorted((ROOT / folder).rglob("*.py")):
            if "__pycache__" in path.parts or (path.name == "__init__.py" and detail == "summary"):
                continue
            parts += [python_module(path, detail), ""]

    parts += ["## Web UI", "", "Plain JavaScript, no build step. Business rules live on the server; the UI shows what the API returns.", ""]
    parts += [javascript_section(), ""]

    parts += ["## End-to-end page objects", "", "Playwright page objects. Elements are found by role or label only.", ""]
    for relative in ("e2e/pages/LoginPage.ts", "e2e/pages/ApprovalsPage.ts"):
        parts += [typescript_section(relative), ""]

    OUTPUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(parts)} blocks)")


if __name__ == "__main__":
    main()
