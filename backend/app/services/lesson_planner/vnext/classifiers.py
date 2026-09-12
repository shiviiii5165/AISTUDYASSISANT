"""
Context Classifiers for Lesson Planner VNext
============================================
Fast, zero-LLM deterministic classification for:
1. Teaching Intent (11 canonical intents)
2. Canonical Academic Domain (CS, SE, ECE, EE, Physics, Chemistry, Math, etc.)
3. Topic Volatility (LOW, MEDIUM, HIGH) determining freshness vs authority weighting.
"""

import re
from typing import Optional, Tuple, Dict, Any
from ..schemas import (
    CanonicalDomain, TeachingIntent, TopicVolatility,
    InstructionalMode, HierarchicalDomain
)


class IntentClassifier:
    """
    Deterministic rule-based intent engine for classifying why a lesson exists.
    Zero-compute fast path with regex keyword heuristics.
    """

    INTENT_PATTERNS = [
        (TeachingIntent.INTERVIEW_PREP, [
            r"\binterview\b", r"\bplacement\b", r"\bleetcode\b", r"\bfaang\b",
            r"\bcoding round\b", r"\bcampus prep\b", r"\bhiring\b", r"\bjob prep\b"
        ]),
        (TeachingIntent.EXAM_PREP, [
            r"\bexam\b", r"\bmidsem\b", r"\bendsem\b", r"\bboard\b", r"\bgate\b",
            r"\bjee\b", r"\bneet\b", r"\bviva\b", r"\bquestion paper\b", r"\bmarks\b"
        ]),
        (TeachingIntent.PROJECT, [
            r"\bproject\b", r"\bbuild\b", r"\bcapstone\b", r"\bapplication\b",
            r"\bmini project\b", r"\bfullstack app\b"
        ]),
        (TeachingIntent.RESEARCH, [
            r"\bresearch\b", r"\bpaper\b", r"\bliterature\b", r"\bphd\b",
            r"\bfrontier\b", r"\bstate of the art\b", r"\barxiv\b", r"\bnovel\b"
        ]),
        (TeachingIntent.IMPLEMENT, [
            r"\bimplement\b", r"\bhands[- ]on\b", r"\bcode\b", r"\bcoding\b",
            r"\blab\b", r"\bprogramming\b", r"\bdebugging\b"
        ]),
        (TeachingIntent.PRACTICE, [
            r"\bpractice\b", r"\bexercise\b", r"\bproblem set\b", r"\bworksheet\b",
            r"\bdrill\b", r"\bsolve\b"
        ]),
        (TeachingIntent.ASSESS, [
            r"\bassess\b", r"\bquiz\b", r"\btest\b", r"\bevaluation\b", r"\bdiagnostic\b"
        ]),
        (TeachingIntent.REVISE, [
            r"\brevise\b", r"\brevision\b", r"\brecap\b", r"\bsummary\b",
            r"\brefresher\b", r"\bcrash course\b", r"\bquick review\b"
        ]),
        (TeachingIntent.INTRODUCE, [
            r"\bintroduce\b", r"\bintro\b", r"\bbeginner\b", r"\bfirst look\b",
            r"\boverview\b", r"\bbasics\b", r"\bwhat is\b"
        ]),
        (TeachingIntent.UNDERSTAND, [
            r"\bunderstand\b", r"\bintuition\b", r"\bmental model\b", r"\bdeep dive\b",
            r"\bconcept\b", r"\btheory\b", r"\bwhy does\b"
        ]),
    ]

    @classmethod
    def classify(cls, text: str, default: TeachingIntent = TeachingIntent.TEACH) -> TeachingIntent:
        """
        Classifies teaching intent from prompt, goal, or class type description.
        """
        if not text:
            return default

        lower_text = text.lower()
        for intent, patterns in cls.INTENT_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, lower_text):
                    return intent

        return default

    @classmethod
    def classify_two_tier(
        cls,
        text: str,
        default_intent: TeachingIntent = TeachingIntent.TEACH,
        default_mode: InstructionalMode = InstructionalMode.STANDARD
    ) -> Tuple[TeachingIntent, InstructionalMode]:
        """
        Two-tier taxonomy: separates primary pedagogical intent from instructional execution mode.
        Example: (TeachingIntent.IMPLEMENT, InstructionalMode.LAB)
        """
        primary_intent = cls.classify(text, default=default_intent)
        
        if not text:
            return primary_intent, default_mode

        lower_text = text.lower()
        mode = default_mode

        if re.search(r"\blab\b|\bhands[- ]on\b|\bpractical session\b", lower_text):
            mode = InstructionalMode.LAB
        elif re.search(r"\bflipped\b|\bpre[- ]class\b", lower_text):
            mode = InstructionalMode.FLIPPED
        elif re.search(r"\bremedial\b|\bcatch[- ]up\b|\bbridge course\b", lower_text):
            mode = InstructionalMode.REMEDIAL
        elif re.search(r"\bsocratic\b|\binquiry\b|\bdialectic\b", lower_text):
            mode = InstructionalMode.SOCRATIC
        elif re.search(r"\bseminar\b|\bcolloquium\b|\bpaper presentation\b", lower_text):
            mode = InstructionalMode.SEMINAR
        elif re.search(r"\bmicro\b|\b5[- ]min\b|\bbite[- ]sized\b", lower_text):
            mode = InstructionalMode.MICRO_LESSON
        elif re.search(r"\bdeep[- ]dive\b|\bin[- ]depth\b", lower_text):
            mode = InstructionalMode.DEEP_DIVE
        elif re.search(r"\bproject kickoff\b|\bcapstone start\b", lower_text):
            mode = InstructionalMode.PROJECT_KICKOFF

        return primary_intent, mode


class DomainClassifier:
    """
    Classifies a topic into a canonical academic domain to govern
    pedagogy, visual selection, and authoritative resource routing.
    """

    DOMAIN_KEYWORDS = [
        (CanonicalDomain.SOFTWARE_ENGINEERING, [
            r"\breact\b", r"\bvue\b", r"\bangular\b", r"\bnext\.?js\b", r"\bnode\.?js\b",
            r"\bfrontend\b", r"\bbackend\b", r"\bdevops\b", r"\bdocker\b", r"\bkubernetes\b",
            r"\bapi\b", r"\brest\b", r"\bgit\b", r"\bsystem design\b", r"\bmicroservices\b",
            r"\bagile\b", r"\btesting\b", r"\bci/cd\b", r"\bweb development\b"
        ]),
        (CanonicalDomain.COMPUTER_SCIENCE, [
            r"\bdata structure\b", r"\balgorithm\b", r"\bbst\b", r"\bbinary tree\b",
            r"\bbinary search\b", r"\bavl\b", r"\bheap\b", r"\bstack\b", r"\bqueue\b",
            r"\blinked list\b", r"\btree\b", r"\btrees\b", r"\bhashing\b", r"\bsorting\b",
            r"\bdynamic programming\b", r"\bgraph\b", r"\bdfs\b", r"\bbfs\b",
            r"\bcompiler\b", r"\boperating system\b", r"\bprocess\b", r"\bthread\b",
            r"\bdbms\b", r"\bdatabase\b", r"\bsql\b", r"\bnormalization\b", r"\bconcurrency\b",
            r"\bcomputer network\b", r"\btcp\b", r"\bip\b", r"\brouting\b", r"\bcryptography\b",
            r"\bautomata\b", r"\btoc\b", r"\bcomplexity\b", r"\bmachine learning\b", r"\bllm\b"
        ]),
        (CanonicalDomain.ECE, [
            r"\bmicroprocessor\b", r"\bmicrocontroller\b", r"\b8085\b", r"\b8086\b", r"\barm\b",
            r"\besp32\b", r"\bvlsi\b", r"\bverilog\b", r"\bvhdl\b", r"\bfpga\b",
            r"\bsignal processing\b", r"\bdsp\b", r"\btelecom\b", r"\b5g\b", r"\bantenna\b",
            r"\bcommunication system\b", r"\bsemiconductor\b", r"\bcmos\b", r"\bmimo\b", r"\bmassive mimo\b"
        ]),
        (CanonicalDomain.ELECTRONICS, [
            r"\bdiode\b", r"\btransistor\b", r"\bbjt\b", r"\bfet\b", r"\bmosfet\b",
            r"\bop[- ]amp\b", r"\bamplifier\b", r"\boscillator\b", r"\banalog electronics\b",
            r"\bdigital electronics\b", r"\blogic gate\b"
        ]),
        (CanonicalDomain.ELECTRICAL, [
            r"\btransformer\b", r"\binduction motor\b", r"\bsynchronous machine\b",
            r"\bpower system\b", r"\bcircuit theory\b", r"\bkirchhoff\b", r"\bcontrol system\b",
            r"\btransmission line\b", r"\belectromagnetism\b", r"\bac circuit\b"
        ]),
        (CanonicalDomain.MATHEMATICS, [
            r"\bcalculus\b", r"\bderivative\b", r"\bintegral\b", r"\blinear algebra\b",
            r"\bmatrix\b", r"\beigen\w*\b", r"\blinear transformation\b", r"\bvector\b",
            r"\bprobability\b", r"\bstatistics\b", r"\balgebra\b",
            r"\bdiscrete math\b", r"\bcombinatorics\b", r"\bdifferential equation\b",
            r"\bcomplex analysis\b", r"\btopology\b", r"\bpythagor\b", r"\bgeometry\b"
        ]),
        (CanonicalDomain.PHYSICS, [
            r"\bnewton\b", r"\bkinematics\b", r"\bthermodynamics\b", r"\boptics\b",
            r"\bquantum\b", r"\brelativity\b", r"\belectrostatics\b", r"\bmagnetism\b",
            r"\bwave\b", r"\bharmonic motion\b", r"\bfriction\b", r"\bgravitation\b"
        ]),
        (CanonicalDomain.CHEMISTRY, [
            r"\borganic chemistry\b", r"\binorganic chemistry\b", r"\bperiodic table\b",
            r"\bchemical bond\b", r"\bkinetics\b", r"\bthermo chemistry\b", r"\bpolymer\b",
            r"\belectrochemistry\b", r"\bstoichiometry\b", r"\bacids and bases\b"
        ]),
        (CanonicalDomain.BIOLOGY, [
            r"\bgenetics\b", r"\bdna\b", r"\brna\b", r"\bcell biology\b", r"\bmitosis\b",
            r"\bmeiosis\b", r"\becology\b", r"\bevolution\b", r"\bphotosynthesis\b",
            r"\bzoology\b", r"\bbotany\b"
        ]),
        (CanonicalDomain.MEDICINE, [
            r"\banatomy\b", r"\bphysiology\b", r"\bpathology\b", r"\bpharmacology\b",
            r"\bcardiology\b", r"\bneurology\b", r"\bclinical\b", r"\bepidemiology\b",
            r"\bsurgery\b", r"\bdiagnosis\b"
        ]),
        (CanonicalDomain.EDUCATION, [
            r"\bpedagogy\b", r"\bcurriculum design\b", r"\bbloom'?s\b", r"\bformative assessment\b",
            r"\blearning theory\b", r"\bclassroom management\b", r"\bandragogy\b"
        ]),
        (CanonicalDomain.ECONOMICS, [
            r"\bmicroeconomics\b", r"\bmacroeconomics\b", r"\binflation\b", r"\bgdp\b",
            r"\bfiscal policy\b", r"\bmonetary policy\b", r"\belasticity\b", r"\bmarket structure\b"
        ]),
        (CanonicalDomain.BUSINESS, [
            r"\bmarketing\b", r"\baccounting\b", r"\bfinance\b", r"\borganizational behavior\b",
            r"\bstrategic management\b", r"\bsupply chain\b", r"\bentrepreneurship\b"
        ]),
    ]

    @classmethod
    def classify(cls, text: str, default: CanonicalDomain = CanonicalDomain.GENERAL_ACADEMIC) -> CanonicalDomain:
        """
        Classifies subject matter into a canonical academic domain.
        """
        if not text:
            return default

        lower_text = text.lower()
        for domain, patterns in cls.DOMAIN_KEYWORDS:
            for pattern in patterns:
                if re.search(pattern, lower_text):
                    return domain

        return default

    @classmethod
    def classify_hierarchical(cls, topic: str, text: str = "") -> HierarchicalDomain:
        """
        Hierarchical domain classification distinguishing specialized sub-disciplines:
        - ECE Communications / Massive MIMO (domain=ECE, spec='communications')
        - React API Frameworks (domain=SOFTWARE_ENGINEERING, spec='web_frameworks')
        - Theoretical CS Algorithms (domain=COMPUTER_SCIENCE, spec='algorithms')
        - Biomedical Engineering / Science (domain=MEDICINE/BIOLOGY, spec='biomedical')
        """
        combined = f"{topic} {text}".lower()
        domain = cls.classify(combined)

        domain_family = "engineering"
        specialization = None

        if domain == CanonicalDomain.ECE:
            domain_family = "engineering"
            if re.search(r"\bmimo\b|\b5g\b|\b6g\b|\bantenna\b|\btelecom\b|\bchannel\b|\bradio\b", combined):
                specialization = "communications"
            elif re.search(r"\bvlsi\b|\bverilog\b|\bvhdl\b|\bfpga\b|\bcmos\b", combined):
                specialization = "vlsi_microelectronics"
            elif re.search(r"\bdsp\b|\bsignal processing\b|\ffft\b", combined):
                specialization = "signal_processing"
            else:
                specialization = "embedded_hardware"

        elif domain == CanonicalDomain.SOFTWARE_ENGINEERING:
            domain_family = "engineering"
            if re.search(r"\breact\b|\bvue\b|\bnext\.?js\b|\bfrontend\b|\bweb\b", combined):
                specialization = "web_frameworks"
            elif re.search(r"\bapi\b|\brest\b|\bgraphql\b|\bbackend\b|\bmicroservices\b", combined):
                specialization = "backend_apis"
            elif re.search(r"\bdevops\b|\bdocker\b|\bkubernetes\b|\bci/cd\b", combined):
                specialization = "cloud_devops"
            else:
                specialization = "software_architecture"

        elif domain == CanonicalDomain.COMPUTER_SCIENCE:
            domain_family = "engineering"
            if re.search(r"\bdynamic programming\b|\btree\b|\bgraph\b|\bsorting\b|\balgorithm\b", combined):
                specialization = "algorithms"
            elif re.search(r"\bdbms\b|\bdatabase\b|\bsql\b", combined):
                specialization = "databases"
            elif re.search(r"\boperating system\b|\bthread\b|\bprocess\b", combined):
                specialization = "systems"
            else:
                specialization = "theoretical_cs"

        elif domain in [CanonicalDomain.PHYSICS, CanonicalDomain.CHEMISTRY, CanonicalDomain.MATHEMATICS]:
            domain_family = "sciences"
            if re.search(r"\bquantum\b", combined):
                specialization = "quantum"
            elif re.search(r"\bcalculus\b|\balgebra\b", combined):
                specialization = "pure_math"

        elif domain in [CanonicalDomain.BIOLOGY, CanonicalDomain.MEDICINE]:
            domain_family = "sciences" if domain == CanonicalDomain.BIOLOGY else "medicine"
            if re.search(r"\bbiomedical\b|\bprosthetic\b|\bbioinformatics\b", combined):
                specialization = "biomedical"
            elif re.search(r"\bphotosynthesis\b|\bbotany\b", combined):
                specialization = "botany"

        elif domain in [CanonicalDomain.ECONOMICS, CanonicalDomain.BUSINESS]:
            domain_family = "business"

        elif domain in [CanonicalDomain.HUMANITIES, CanonicalDomain.LAW, CanonicalDomain.SOCIAL_SCIENCES, CanonicalDomain.LANGUAGES]:
            domain_family = "humanities"

        return HierarchicalDomain(
            domain_family=domain_family,
            domain=domain,
            specialization=specialization
        )


class TopicVolatilityClassifier:
    """
    Evaluates whether a topic is static/foundational (LOW), evolving (MEDIUM),
    or fast-moving / frontier (HIGH).
    
    Affects:
    - YouTube ranking freshness multiplier
    - Official documentation priority over secondary blogs
    - Research paper recency window
    """

    HIGH_VOLATILITY_PATTERNS = [
        r"\breact 1[89]\b", r"\bnext\.?js 1[4-9]\b", r"\bllm\b", r"\bgpt-[45]\b",
        r"\blangchain\b", r"\bllama[- ]?3\b", r"\bgenerative ai\b", r"\brag architecture\b",
        r"\bvision transformer\b", r"\bmodern semiconductor\b", r"\b3nm\b", r"\b2nm\b",
        r"\bwi-?fi 7\b", r"\b5g advanced\b", r"\b6g\b", r"\bquantum computing hardware\b",
        r"\bwebgpu\b", r"\btailwind v4\b", r"\bkubernetes\b", r"\bcloud native\b"
    ]

    MEDIUM_VOLATILITY_PATTERNS = [
        r"\bpython 3\.[1-9]\d\b", r"\bc\+\+2[03]\b", r"\bhttp\/?3\b", r"\bquic\b",
        r"\brust language\b", r"\bflutter\b", r"\bswiftui\b", r"\bcybersecurity\b",
        r"\bzero trust\b", r"\bcloud security\b", r"\bmicroservices\b", r"\bkafka\b"
    ]

    @classmethod
    def classify(cls, topic: str, domain: Optional[CanonicalDomain] = None) -> TopicVolatility:
        if not topic:
            return TopicVolatility.LOW

        lower = topic.lower()

        for pat in cls.HIGH_VOLATILITY_PATTERNS:
            if re.search(pat, lower):
                return TopicVolatility.HIGH

        for pat in cls.MEDIUM_VOLATILITY_PATTERNS:
            if re.search(pat, lower):
                return TopicVolatility.MEDIUM

        # Software engineering topics default to MEDIUM volatility unless foundational
        if domain == CanonicalDomain.SOFTWARE_ENGINEERING:
            return TopicVolatility.MEDIUM

        # Timeless foundational domains (Math, Classic Physics, Classic CS) default to LOW
        return TopicVolatility.LOW

    @classmethod
    def get_freshness_weight(cls, volatility: TopicVolatility) -> float:
        """
        Returns the weight boost for freshness in scoring algorithms.
        """
        if volatility == TopicVolatility.HIGH:
            return 2.5  # Heavy weight on recent updates
        elif volatility == TopicVolatility.MEDIUM:
            return 1.4  # Moderate freshness bonus
        return 1.0  # Standard weight: quality and pedagogical clarity dominate
