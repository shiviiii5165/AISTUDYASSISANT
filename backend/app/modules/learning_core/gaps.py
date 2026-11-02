"""Stage 3: find the root prerequisite gaps behind an E02 error."""
from __future__ import annotations

from typing import Callable, Mapping, Sequence


def remediation_path(
    skill_id: str,
    prerequisites: Mapping[str, Sequence[str]],
    is_weak: Callable[[str], bool],
) -> list[str]:
    """Return weak ancestors in teach-first order, with the root gaps at the front.

    Traversal stops at secure prerequisites: a gap behind a secure skill does not
    explain this error. skill_id itself is excluded. Cycles are tolerated here so
    that bad graph data cannot hang a request; the database trigger rejects them.
    """
    ordered: list[str] = []
    visited = {skill_id}

    def visit(node: str) -> None:
        for prerequisite in sorted(prerequisites.get(node, ())):
            if prerequisite not in visited and is_weak(prerequisite):
                visited.add(prerequisite)
                visit(prerequisite)
                ordered.append(prerequisite)

    visit(skill_id)
    return ordered
