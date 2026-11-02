"""Facts about a student that cross module boundaries."""
from __future__ import annotations

import re
from typing import Optional

from app.services.learner_context.service import LearnerContextService


def student_class(student_id: str) -> Optional[int]:
    """Return the student's class from their profile, or None when it isn't a school class."""
    grade = LearnerContextService.get_profile(student_id).grade_or_class or ""
    match = re.search(r"\b(\d{1,2})\b", grade)
    return int(match.group(1)) if match else None
