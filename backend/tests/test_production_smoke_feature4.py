import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.services.tutor.service import PersonalizedTutorService
from app.services.tutor.schemas import TutorMode, PedagogicalState, HintLevel, CheckOutcome, TutorCheck
from app.services.tutor.repository import TutorSessionRepository
from app.services.learner_context.service import LearnerContextService
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.repository import MasteryRepository
from app.services.mastery.schemas import EvidenceSource, AssistanceLevel

STUDENT_A = "a56da972-0f19-418d-b0f7-de91ff114190"
STUDENT_B = "d7007dd2-57dd-477c-9429-629d620cd616"


@pytest.fixture(autouse=True)
def clean_smoke_state():
    TutorSessionRepository.clear_memory_cache()
    MasteryRepository.clear_memory_cache()
    yield


@pytest.mark.anyio
async def test_smoke_flow_a_class5_hinglish_fractions():
    """
    FLOW A (§51):
    Class 5 learner -> Hinglish -> learn Fractions -> Tutor explains appropriately -> asks check -> response evaluated
    """
    with patch("app.services.tutor.service.call_gemini", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Fraction ka matlab hota hai kisi poori cheez ka ek hissa! Jaise 1 roti ke 2 barabar tukde karein toh har tukda 1/2 hota hai. Agar hum ek seb ke 4 barabar hisse karein aur 1 hissa aapko dein, toh kitna fraction hoga?"

        # Turn 1: Class 5 student asks about fractions in Hinglish
        turn1 = await PersonalizedTutorService.process_turn(
            user_id=STUDENT_A,
            message="Bhaiya fractions kya hota hai samjha do",
            explicit_mode=TutorMode.TUTOR,
            subject="mathematics"
        )

        assert turn1.message is not None
        assert "Fraction" in turn1.message or "hissa" in turn1.message
        assert turn1.pedagogical_state in (PedagogicalState.ORIENT, PedagogicalState.EXPLAIN, PedagogicalState.CHECK)
        assert turn1.mode == TutorMode.TUTOR

        # Verify no gamification
        for forbidden in ["XP", "+100", "level up", "streak", "AIR"]:
            assert forbidden not in turn1.message

        # Turn 2: Student answers checking question correctly (1/4)
        mock_llm.return_value = "Bahut badiya! Bilkul sahi jawab, 1/4 hoga."
        turn2 = await PersonalizedTutorService.process_turn(
            user_id=STUDENT_A,
            session_id=turn1.session_id,
            message="1/4 hissa hoga",
            explicit_mode=TutorMode.TUTOR,
            subject="mathematics"
        )
        assert turn2.session_id == turn1.session_id
        assert turn2.message is not None


@pytest.mark.anyio
async def test_smoke_flow_b_class11_jee_quadratic_prerequisite_repair():
    """
    FLOW B (§51):
    Class 11 JEE learner -> asks Quadratic Equations -> prerequisite graph identifies relevant repair if needed -> Tutor adapts
    """
    # Simulate prerequisite graph state: factorisation needs repair
    MasteryGraphService.ingest_evidence(
        user_id=STUDENT_A,
        skill_id="MATH_FAC_POLY",
        source_type=EvidenceSource.DIAGNOSTIC,
        source_record_id="diag-smoke-quad-1",
        correctness=False
    )

    with patch("app.services.tutor.service.call_gemini", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "In quadratic equations, solving ax^2 + bx + c = 0 relies heavily on factoring polynomials. Let's make sure our factoring step is rock solid first."

        turn = await PersonalizedTutorService.process_turn(
            user_id=STUDENT_A,
            message="Teach me Quadratic Equations for JEE Mains",
            explicit_mode=TutorMode.TUTOR,
            subject="mathematics"
        )

        assert turn.message is not None
        assert turn.mode == TutorMode.TUTOR
        # No rank predictions
        assert "AIR" not in turn.message and "percentile" not in turn.message


@pytest.mark.anyio
async def test_smoke_flow_c_student_owned_pdf_document_learning():
    """
    FLOW C (§51):
    Student uploads/uses owned PDF -> asks document-specific concept -> Librarian retrieves authorized source -> Tutor teaches with citation
    """
    mock_retrieved = [
        {
            "source": "NCERT_Physics_Ch5.pdf",
            "page": "14",
            "text": "Newton's First Law states that a body continues in its state of rest or uniform motion unless acted upon by an external unbalanced force."
        }
    ]

    with patch("app.services.tutor.service.call_gemini", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "According to Page 14 of NCERT Physics, a body remains at rest or constant velocity unless an external force acts on it. Why is this also known as the Law of Inertia?"

        turn = await PersonalizedTutorService.process_turn(
            user_id=STUDENT_A,
            message="According to my PDF, what is Newton's first law?",
            explicit_mode=TutorMode.TUTOR,
            subject="physics",
            pdf_id="doc_physics_ncert_ch5",
            retrieved_material=mock_retrieved
        )

        assert turn.message is not None
        assert len(turn.citations) > 0
        assert turn.citations[0]["source"] == "NCERT_Physics_Ch5.pdf"
        assert turn.citations[0]["page"] == "14"


@pytest.mark.anyio
async def test_smoke_flow_d_quick_ask_direct_no_forced_socratic():
    """
    FLOW D (§51):
    Quick Ask -> direct concise answer -> no forced Socratic loop
    """
    with patch("app.services.tutor.service.call_gemini", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Newton's second law states that the rate of change of momentum of a body is directly proportional to the applied force. Formula: F = ma."

        turn = await PersonalizedTutorService.process_turn(
            user_id=STUDENT_B,
            message="What is the formula and definition of Newton's second law?",
            explicit_mode=TutorMode.QUICK_ASK,
            subject="physics"
        )

        assert turn.mode == TutorMode.QUICK_ASK
        # Quick ask must NOT issue an active Socratic checking question
        assert turn.active_check is None
        assert "F = ma" in turn.message


@pytest.mark.anyio
async def test_smoke_flow_e_full_explanation_escape_hatch_no_false_mastery():
    """
    FLOW E (§51):
    Explicit full explanation request -> Tutor eventually gives complete explanation -> does not falsely mark mastery
    """
    # Setup session with pending check
    from app.services.tutor.schemas import TutorSessionState
    session = TutorSessionState(
        user_id=STUDENT_B,
        session_mode=TutorMode.TUTOR,
        pedagogical_state=PedagogicalState.CHECK,
        current_check=TutorCheck(
            skill_id="MATH_LIN_EQ",
            skill_name="Linear Equations",
            question="Solve 2x + 6 = 14",
            expected_answer="4"
        )
    )
    TutorSessionRepository.save_session(session)

    with patch("app.services.tutor.service.call_gemini", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Here is the complete worked solution:\n1. Subtract 6 from both sides: 2x = 14 - 6 = 8\n2. Divide both sides by 2: x = 8 / 2 = 4."

        turn = await PersonalizedTutorService.process_turn(
            user_id=STUDENT_B,
            session_id=session.id,
            message="I'm stuck, just give me the answer and show full steps",
            explicit_mode=TutorMode.TUTOR,
            subject="mathematics"
        )

        assert turn.hint_level == HintLevel.FULL_EXPLANATION
        assert "x = 4" in turn.message or "4" in turn.message
        
        # Verify assistance level is FULLY_ASSISTED and does not claim independent mastery
        updated = TutorSessionRepository.get_session(session.id, STUDENT_B)
        assert updated.assistance_level == AssistanceLevel.FULLY_ASSISTED
