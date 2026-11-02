"""Seed the Class 8-10 MVP: skills, prerequisite DAG, retrieval chunks and IRT parameters.

Run from backend/ after migrations 033 and 034:   python scripts/seed_ncert_mvp.py
Writes to the Supabase project in your environment, and is safe to re-run.
Use --dry-run to validate the content without writing anything.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules import store  # noqa: E402
from app.modules.curriculum.items import all_items  # noqa: E402
from app.modules.curriculum.ncert_seed import CONCEPTS, build_chunks  # noqa: E402
from app.modules.learning_core.math_verifier import Verdict, verify_derivation  # noqa: E402


def validate() -> list[str]:
    problems = []
    known = {c.concept_id for c in CONCEPTS}
    for concept in CONCEPTS:
        if not concept.citation_id.startswith(f"NCERT-C{concept.class_level}-"):
            problems.append(f"{concept.concept_id}: bad citation {concept.citation_id}")
        for link in concept.prerequisites + concept.siblings:
            if link not in known:
                problems.append(f"{concept.concept_id}: unknown concept {link}")
        if concept.subject == "Mathematics":
            if verify_derivation(concept.worked_steps).verdict is not Verdict.VERIFIED:
                problems.append(f"{concept.concept_id}: worked example failed verification")
    return problems


def seed() -> dict[str, int]:
    counts = {"skills": 0, "edges": 0, "chunks": 0, "irt": 0}
    for concept in CONCEPTS:
        store.upsert("ncert_concepts", {
            "concept_id": concept.concept_id, "class_level": concept.class_level,
            "subject": concept.subject, "title": concept.title,
            "citation_id": concept.citation_id, "prerequisites": list(concept.prerequisites),
        }, ("concept_id",))
        counts["skills"] += 1
    for chunk in build_chunks():
        store.upsert("ncert_chunks", chunk, ("chunk_id",))
        counts["chunks"] += 1
    for concept in CONCEPTS:
        counts["edges"] += len(concept.prerequisites)
    for item in all_items():
        store.upsert("item_irt_parameters", {
            "item_id": item.item_id, "model": "2PL", "b": item.b, "a": item.irt.a, "c": item.irt.c,
            "calibration_status": "provisional", "sample_size": 0,
        }, ("item_id",))
        counts["irt"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    problems = validate()
    if problems:
        print("\n".join(problems))
        return 1
    print(f"Valid: {len(CONCEPTS)} concepts, {len(build_chunks())} chunks, {len(all_items())} items.")
    if not args.dry_run:
        print(seed())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
