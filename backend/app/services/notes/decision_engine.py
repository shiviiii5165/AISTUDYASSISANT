"""
AI Notes Generation Engine — Deterministic Decision Engine
===========================================================
Backward-compatibility bridge delegating to the unified Step 2 Decision Engine.
Answers: "Given what TeachGenie knows, what does this learner actually need in their notes?"
"""
from typing import List, Set

from .schemas import (
    CanonicalNotesContext, DecisionOutput,
    NoteFormat, NoteDepth, NoteDifficulty
)
from .decision import NotesDecisionEngine, decide_notes_plan, GradePolicy

# Backward compatibility alias
__all__ = ["NotesDecisionEngine", "decide_notes_plan"]
