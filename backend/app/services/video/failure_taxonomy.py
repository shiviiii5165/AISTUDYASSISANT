"""
LearnByGenie AI Video Teacher V2.2 — Centralized Failure Taxonomy
==============================================================
Implements Decision #13:
- Structured failure codes across LLM, TTS, Visualizer, FFmpeg, Storage, DB, QA.
- Strict boundary between safe student-facing messages and internal diagnostics.
- Student-facing responses NEVER expose stack traces, secrets, or internal provider keys.
"""
import traceback
from typing import Dict, Any, Optional
from .schemas import FailureCode, FailureDetail


# Canonical failure definitions with student-safe messages and retry/recovery semantics
FAILURE_CATALOG: Dict[FailureCode, Dict[str, Any]] = {
    FailureCode.LLM_TIMEOUT: {
        "severity": "ERROR",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "The AI teaching assistant took longer than expected to prepare this explanation. Please click Retry to try again.",
    },
    FailureCode.LLM_INVALID_OUTPUT: {
        "severity": "ERROR",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "We couldn't structure this educational concept properly on the first attempt. Please try rephrasing or retrying.",
    },
    FailureCode.CURRICULUM_GENERATION_FAILED: {
        "severity": "ERROR",
        "recoverable": False,
        "retryable": True,
        "safe_user_message": "We encountered an issue assembling the lesson roadmap for this topic. Please retry in a few moments.",
    },
    FailureCode.TTS_PRIMARY_FAILED: {
        "severity": "WARNING",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "Switching to secondary voice engine for smooth narration.",
    },
    FailureCode.TTS_ALL_PROVIDERS_FAILED: {
        "severity": "CRITICAL",
        "recoverable": False,
        "retryable": True,
        "safe_user_message": "Audio narration could not be generated. Please retry or generate with captions only.",
    },
    FailureCode.VISUALIZER_FAILED: {
        "severity": "WARNING",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "A visual diagram could not be rendered, so we adapted the visual style to keep your lesson moving.",
    },
    FailureCode.FFMPEG_FAILED: {
        "severity": "CRITICAL",
        "recoverable": False,
        "retryable": True,
        "safe_user_message": "Video rendering failed during composition. Please retry generating the lesson.",
    },
    FailureCode.MEDIA_CORRUPT: {
        "severity": "ERROR",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "One of the visual clips was corrupted during rendering. We are repairing and regenerating.",
    },
    FailureCode.STORAGE_UPLOAD_FAILED: {
        "severity": "WARNING",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "Your lesson video was compiled successfully and is available locally, though cloud sync is delayed.",
    },
    FailureCode.DATABASE_WRITE_FAILED: {
        "severity": "ERROR",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "Lesson saved in active session, but database synchronization was delayed.",
    },
    FailureCode.SOURCE_RETRIEVAL_FAILED: {
        "severity": "WARNING",
        "recoverable": True,
        "retryable": True,
        "safe_user_message": "Could not retrieve external document sources; proceeding with core academic knowledge base.",
    },
    FailureCode.QUALITY_GATE_FAILED: {
        "severity": "WARNING",
        "recoverable": True,
        "retryable": False,
        "safe_user_message": "Lesson quality fell below our certified teaching standards and was automatically repaired.",
    },
    FailureCode.UNKNOWN_INTERNAL_ERROR: {
        "severity": "CRITICAL",
        "recoverable": False,
        "retryable": True,
        "safe_user_message": "An unexpected error occurred while preparing your lesson. Our team has been notified. Please click Retry.",
    },
}


class FailureTaxonomy:
    """Classifies system errors into structured FailureDetails (Decision #13)."""

    @classmethod
    def create_failure(
        cls,
        code: FailureCode,
        internal_diagnostic: str,
        custom_safe_message: Optional[str] = None
    ) -> FailureDetail:
        """Constructs a typed FailureDetail adhering to privacy and safety guarantees."""
        meta = FAILURE_CATALOG.get(code, FAILURE_CATALOG[FailureCode.UNKNOWN_INTERNAL_ERROR])
        return FailureDetail(
            code=code,
            severity=meta["severity"],
            recoverable=meta["recoverable"],
            retryable=meta["retryable"],
            safe_user_message=custom_safe_message or meta["safe_user_message"],
            internal_diagnostic=internal_diagnostic,
        )

    @classmethod
    def classify_exception(cls, exc: Exception, context_hint: Optional[str] = None) -> FailureDetail:
        """Automatically categorizes an arbitrary exception into the structured failure taxonomy."""
        exc_str = str(exc).lower()
        diag = f"{type(exc).__name__}: {str(exc)} | Hint: {context_hint or 'none'} | {traceback.format_exc()}"

        if "timeout" in exc_str or "timed out" in exc_str or "deadline" in exc_str:
            code = FailureCode.LLM_TIMEOUT
        elif "json" in exc_str or "pydantic" in exc_str or "validation" in exc_str or "parse" in exc_str:
            code = FailureCode.LLM_INVALID_OUTPUT
        elif "tts" in exc_str or "audio" in exc_str or "voice" in exc_str:
            code = FailureCode.TTS_ALL_PROVIDERS_FAILED
        elif "ffmpeg" in exc_str or "mux" in exc_str or "concat" in exc_str:
            code = FailureCode.FFMPEG_FAILED
        elif "storage" in exc_str or "s3" in exc_str or "supabase.storage" in exc_str:
            code = FailureCode.STORAGE_UPLOAD_FAILED
        elif "database" in exc_str or "postgres" in exc_str or "supabase.table" in exc_str:
            code = FailureCode.DATABASE_WRITE_FAILED
        elif "visual" in exc_str or "matplotlib" in exc_str or "pillow" in exc_str or "cv2" in exc_str:
            code = FailureCode.VISUALIZER_FAILED
        else:
            code = FailureCode.UNKNOWN_INTERNAL_ERROR

        return cls.create_failure(code=code, internal_diagnostic=diag)

    @classmethod
    def to_student_payload(cls, failure: FailureDetail) -> Dict[str, Any]:
        """
        Extracts student-facing error information only.
        STRICT GUARANTEE: Never exposes internal_diagnostic, stack traces, or credentials.
        """
        return {
            "error_code": failure.code.value,
            "message": failure.safe_user_message,
            "retryable": failure.retryable,
            "recoverable": failure.recoverable,
            "severity": failure.severity,
        }
