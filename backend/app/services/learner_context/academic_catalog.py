"""
LearnByGenie — Canonical Database-Driven Academic Catalog
Defines canonical education stages, levels (Class 3-12 + UG), curricula,
exam tracks, subjects, goals, and languages.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class EducationStage:
    PRIMARY = "PRIMARY"                   # Class 3 - 5
    MIDDLE = "MIDDLE"                     # Class 6 - 8
    SECONDARY = "SECONDARY"               # Class 9 - 10
    SENIOR_SECONDARY = "SENIOR_SECONDARY" # Class 11 - 12
    EXAM_PREP = "EXAM_PREP"               # Dropper / Dedicated Entrance Prep
    UNDERGRADUATE = "UNDERGRADUATE"       # University Year 1 - 4

# Canonical Education Levels
EDUCATION_LEVELS = [
    {"id": "class_3", "name": "Class 3", "stage": EducationStage.PRIMARY, "display_order": 1, "has_streams": False},
    {"id": "class_4", "name": "Class 4", "stage": EducationStage.PRIMARY, "display_order": 2, "has_streams": False},
    {"id": "class_5", "name": "Class 5", "stage": EducationStage.PRIMARY, "display_order": 3, "has_streams": False},
    {"id": "class_6", "name": "Class 6", "stage": EducationStage.MIDDLE, "display_order": 4, "has_streams": False},
    {"id": "class_7", "name": "Class 7", "stage": EducationStage.MIDDLE, "display_order": 5, "has_streams": False},
    {"id": "class_8", "name": "Class 8", "stage": EducationStage.MIDDLE, "display_order": 6, "has_streams": False},
    {"id": "class_9", "name": "Class 9", "stage": EducationStage.SECONDARY, "display_order": 7, "has_streams": False},
    {"id": "class_10", "name": "Class 10", "stage": EducationStage.SECONDARY, "display_order": 8, "has_streams": False},
    {
        "id": "class_11", 
        "name": "Class 11", 
        "stage": EducationStage.SENIOR_SECONDARY, 
        "display_order": 9, 
        "has_streams": True,
        "allowed_streams": ["science_pcm", "science_pcb", "commerce", "humanities", "general"]
    },
    {
        "id": "class_12", 
        "name": "Class 12", 
        "stage": EducationStage.SENIOR_SECONDARY, 
        "display_order": 10, 
        "has_streams": True,
        "allowed_streams": ["science_pcm", "science_pcb", "commerce", "humanities", "general"]
    },
    {
        "id": "ug_year_1", 
        "name": "Undergraduate Year 1", 
        "stage": EducationStage.UNDERGRADUATE, 
        "display_order": 11, 
        "has_streams": True,
        "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]
    },
    {
        "id": "ug_year_2", 
        "name": "Undergraduate Year 2", 
        "stage": EducationStage.UNDERGRADUATE, 
        "display_order": 12, 
        "has_streams": True,
        "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]
    },
    {
        "id": "ug_year_3", 
        "name": "Undergraduate Year 3", 
        "stage": EducationStage.UNDERGRADUATE, 
        "display_order": 13, 
        "has_streams": True,
        "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]
    },
    {
        "id": "ug_year_4", 
        "name": "Undergraduate Year 4", 
        "stage": EducationStage.UNDERGRADUATE, 
        "display_order": 14, 
        "has_streams": True,
        "allowed_streams": ["engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"]
    },
]

# Canonical Boards / Curricula
CURRICULA = [
    {"id": "CBSE", "name": "CBSE", "full_name": "Central Board of Secondary Education", "region": "IN"},
    {"id": "ICSE_ISC", "name": "ICSE / ISC", "full_name": "Council for the Indian School Certificate Examinations", "region": "IN"},
    {"id": "STATE_BOARD", "name": "State Board", "full_name": "State Board Curriculum", "region": "IN"},
    {"id": "IB", "name": "IB", "full_name": "International Baccalaureate", "region": "GLOBAL"},
    {"id": "CAMBRIDGE", "name": "Cambridge", "full_name": "Cambridge International (IGCSE / A-Levels)", "region": "GLOBAL"},
    {"id": "UNIVERSITY", "name": "University Curriculum", "full_name": "University / College Degree Coursework", "region": "ALL"},
]

# Canonical Academic Streams
ACADEMIC_STREAMS = [
    {"id": "general", "name": "General Studies", "stages": [EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY]},
    {"id": "science_pcm", "name": "Science (PCM - Physics, Chemistry, Math)", "stages": [EducationStage.SENIOR_SECONDARY, EducationStage.EXAM_PREP]},
    {"id": "science_pcb", "name": "Science (PCB - Physics, Chemistry, Biology)", "stages": [EducationStage.SENIOR_SECONDARY, EducationStage.EXAM_PREP]},
    {"id": "commerce", "name": "Commerce (Accountancy, Economics, Business Studies)", "stages": [EducationStage.SENIOR_SECONDARY]},
    {"id": "humanities", "name": "Humanities / Arts (History, Pol Sci, Psychology)", "stages": [EducationStage.SENIOR_SECONDARY]},
    {"id": "engineering_cs", "name": "Computer Science & Engineering", "stages": [EducationStage.UNDERGRADUATE]},
    {"id": "engineering_core", "name": "Core Engineering (Mechanical, Civil, Electrical)", "stages": [EducationStage.UNDERGRADUATE]},
    {"id": "basic_sciences", "name": "Natural & Basic Sciences", "stages": [EducationStage.UNDERGRADUATE]},
    {"id": "commerce_finance", "name": "Finance & Business Administration", "stages": [EducationStage.UNDERGRADUATE]},
]

# Canonical Exam Tracks
EXAM_TRACKS = [
    {
        "id": "JEE", 
        "name": "JEE (Main & Advanced)", 
        "description": "Joint Entrance Examination for Engineering",
        "eligible_stages": [EducationStage.SENIOR_SECONDARY, EducationStage.EXAM_PREP]
    },
    {
        "id": "NEET", 
        "name": "NEET (UG Medical)", 
        "description": "National Eligibility cum Entrance Test for Medicine",
        "eligible_stages": [EducationStage.SENIOR_SECONDARY, EducationStage.EXAM_PREP]
    },
    {
        "id": "BOARDS", 
        "name": "Board Examinations", 
        "description": "Class 10 or Class 12 Final Board Examinations",
        "eligible_stages": [EducationStage.SECONDARY, EducationStage.SENIOR_SECONDARY]
    },
    {
        "id": "SCHOOL_EXAMS", 
        "name": "School Term Exams", 
        "description": "School Periodic and Annual Assessments",
        "eligible_stages": [EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY]
    },
    {
        "id": "UG_SEMESTER", 
        "name": "University Semester Exams", 
        "description": "College and University End-Semester Coursework",
        "eligible_stages": [EducationStage.UNDERGRADUATE]
    },
    {
        "id": "FOUNDATION", 
        "name": "Concept Mastery & Foundation", 
        "description": "Non-exam focused deep concept learning",
        "eligible_stages": [EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY, EducationStage.SENIOR_SECONDARY, EducationStage.UNDERGRADUATE]
    },
]

# Canonical Subjects Catalog
CANONICAL_SUBJECTS = [
    # Primary & Middle Subjects
    {"id": "english", "name": "English", "category": "Languages"},
    {"id": "hindi", "name": "Hindi", "category": "Languages"},
    {"id": "mathematics", "name": "Mathematics", "category": "STEM"},
    {"id": "science", "name": "Science", "category": "STEM"},
    {"id": "social_science", "name": "Social Science", "category": "Social Studies"},
    {"id": "environmental_studies", "name": "Environmental Studies (EVS)", "category": "Science"},
    
    # Secondary & Senior Secondary STEM
    {"id": "physics", "name": "Physics", "category": "STEM"},
    {"id": "chemistry", "name": "Chemistry", "category": "STEM"},
    {"id": "biology", "name": "Biology", "category": "STEM"},
    {"id": "computer_science", "name": "Computer Science / IP", "category": "STEM"},
    
    # Commerce
    {"id": "accountancy", "name": "Accountancy", "category": "Commerce"},
    {"id": "business_studies", "name": "Business Studies", "category": "Commerce"},
    {"id": "economics", "name": "Economics", "category": "Commerce"},
    
    # Humanities
    {"id": "history", "name": "History", "category": "Humanities"},
    {"id": "political_science", "name": "Political Science", "category": "Humanities"},
    {"id": "geography", "name": "Geography", "category": "Humanities"},
    {"id": "psychology", "name": "Psychology", "category": "Humanities"},
    {"id": "sociology", "name": "Sociology", "category": "Humanities"},

    # Undergraduate
    {"id": "data_structures_algorithms", "name": "Data Structures & Algorithms", "category": "Computer Science"},
    {"id": "operating_systems", "name": "Operating Systems", "category": "Computer Science"},
    {"id": "database_systems", "name": "Database Management Systems", "category": "Computer Science"},
    {"id": "engineering_mathematics", "name": "Engineering Mathematics", "category": "Engineering"},
    {"id": "digital_electronics", "name": "Digital Electronics", "category": "Engineering"},
    {"id": "corporate_finance", "name": "Corporate Finance", "category": "Finance"},
]

# Canonical Academic Goals
ACADEMIC_GOALS = [
    {"id": "subject_mastery", "name": "Improve Subject Mastery", "description": "Build deep, conceptual understanding across target topics"},
    {"id": "board_preparation", "name": "Board Preparation", "description": "Focus on syllabus completion, past year papers, and board writing skills"},
    {"id": "jee_preparation", "name": "JEE Preparation", "description": "Intensive problem-solving and rigorous entrance exam training"},
    {"id": "neet_preparation", "name": "NEET Preparation", "description": "High-accuracy NCERT mastery and speed practice for medical entrance"},
    {"id": "school_revision", "name": "School Revision", "description": "Keep up with school curriculum and periodic tests"},
    {"id": "semester_preparation", "name": "Semester Preparation", "description": "Target university syllabus and semester exam benchmarks"},
    {"id": "concept_learning", "name": "Concept Learning", "description": "Self-paced exploratory learning of specific domains"},
]

# Canonical Languages
LANGUAGES = [
    {"id": "hinglish", "code": "hinglish", "name": "Hinglish", "native_label": "Hinglish (Hindi + English)"},
    {"id": "en", "code": "en", "name": "English", "native_label": "English"},
    {"id": "hi", "code": "hi", "name": "Hindi", "native_label": "हिन्दी"},
    {"id": "bn", "code": "bn", "name": "Bengali", "native_label": "বাংলা"},
    {"id": "ta", "code": "ta", "name": "Tamil", "native_label": "தமிழ்"},
    {"id": "te", "code": "te", "name": "Telugu", "native_label": "తెలుగు"},
    {"id": "mr", "code": "mr", "name": "Marathi", "native_label": "मराठी"},
    {"id": "gu", "code": "gu", "name": "Gujarati", "native_label": "ગુજરાતી"},
    {"id": "kn", "code": "kn", "name": "Kannada", "native_label": "ಕನ್ನಡ"},
]

# Session Lengths
SESSION_DURATIONS = [15, 30, 45, 60]


def get_stage_for_level(level_id: str) -> str:
    """Resolve education stage from education level ID."""
    clean = (level_id or "").strip().lower()
    for lvl in EDUCATION_LEVELS:
        if lvl["id"].lower() == clean or lvl["name"].lower() == clean:
            return lvl["stage"]
    # Fallback heuristic
    if "ug" in clean or "undergrad" in clean or "year" in clean:
        return EducationStage.UNDERGRADUATE
    if any(k in clean for k in ["11", "12"]):
        return EducationStage.SENIOR_SECONDARY
    if any(k in clean for k in ["9", "10"]):
        return EducationStage.SECONDARY
    if any(k in clean for k in ["6", "7", "8"]):
        return EducationStage.MIDDLE
    return EducationStage.PRIMARY


def get_default_subjects_for_level_and_stream(level_id: str, stream: Optional[str] = None) -> List[str]:
    """Provide default subject selections based on academic level and stream."""
    stage = get_stage_for_level(level_id)
    if stage in (EducationStage.PRIMARY, EducationStage.MIDDLE):
        return ["Mathematics", "Science", "English", "Social Science"]
    if stage == EducationStage.SECONDARY:
        return ["Mathematics", "Science", "Social Science", "English"]
    if stage in (EducationStage.SENIOR_SECONDARY, EducationStage.EXAM_PREP):
        st = (stream or "").lower()
        if "pcb" in st or "medical" in st:
            return ["Physics", "Chemistry", "Biology", "English"]
        if "commerce" in st:
            return ["Accountancy", "Business Studies", "Economics", "English"]
        if "humanities" in st or "arts" in st:
            return ["History", "Political Science", "Economics", "English"]
        # Default PCM
        return ["Physics", "Chemistry", "Mathematics", "English"]
    if stage == EducationStage.UNDERGRADUATE:
        return ["Data Structures & Algorithms", "Operating Systems", "Database Management Systems"]
    return ["Mathematics", "Science", "English"]


def get_academic_config_payload() -> Dict[str, Any]:
    """Returns the unified academic config payload from remote database with canonical fallback."""
    try:
        from app.db.supabase_client import supabase
        if supabase is not None:
            res = supabase.table("academic_catalog").select("*").eq("is_active", True).order("display_order").execute()
            if res and res.data and len(res.data) > 0:
                levels = []
                curricula = []
                exams = []
                goals = []
                langs = []
                for row in res.data:
                    cat = row.get("category")
                    code = row.get("code")
                    label = row.get("label")
                    stage = row.get("stage")
                    meta = row.get("metadata") or {}
                    order = row.get("display_order", 0)

                    if cat == "education_level":
                        levels.append({
                            "id": code,
                            "name": label,
                            "stage": stage,
                            "display_order": order,
                            "has_streams": meta.get("has_streams", False),
                            "allowed_streams": meta.get("allowed_streams")
                        })
                    elif cat == "curriculum":
                        curricula.append({
                            "id": code,
                            "name": label,
                            "full_name": label,
                            "region": meta.get("region", "ALL")
                        })
                    elif cat == "exam_track":
                        exams.append({
                            "id": code,
                            "name": label,
                            "description": label,
                            "eligible_stages": meta.get("eligible_stages", [stage])
                        })
                    elif cat == "goal":
                        goals.append({
                            "id": code,
                            "name": label,
                            "description": label
                        })
                    elif cat == "language":
                        langs.append({
                            "id": code,
                            "code": code,
                            "name": label,
                            "native_label": label
                        })

                if levels and curricula and exams and goals and langs:
                    return {
                        "education_levels": levels,
                        "curricula": curricula,
                        "academic_streams": ACADEMIC_STREAMS,
                        "exam_tracks": exams,
                        "subjects": CANONICAL_SUBJECTS,
                        "academic_goals": goals,
                        "languages": langs,
                        "session_durations_minutes": SESSION_DURATIONS,
                    }
    except Exception as e:
        logger.debug("Academic config dynamic loading fallback: %s", e)

    return {
        "education_levels": EDUCATION_LEVELS,
        "curricula": CURRICULA,
        "academic_streams": ACADEMIC_STREAMS,
        "exam_tracks": EXAM_TRACKS,
        "subjects": CANONICAL_SUBJECTS,
        "academic_goals": ACADEMIC_GOALS,
        "languages": LANGUAGES,
        "session_durations_minutes": SESSION_DURATIONS,
    }
