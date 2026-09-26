"""
LearnByGenie Document Renderer — HTML Print Builder
=================================================
Builds a complete, print-optimized, student-friendly HTML document from a NotesDocument.
Enforces explicit modular wrappers to prevent orphaned headings, split formulas,
footer collisions, and awkward page breaks:
- .section-wrapper
- .subsection-wrapper
- .example-wrapper
- .callout-wrapper
- .diagram-wrapper
- .table-wrapper
- .practice-wrapper
- .equation-wrapper
"""
import html
import re
from typing import Optional, Dict, Any, List
from .typesetter import SemanticTypesetter
from ..schemas import NotesDocument, NoteSection, VisualSpec, CalloutItem


class HTMLNoteBuilder:
    """Builds clean, print-accurate, beautifully styled educational HTML for PDF generation."""

    CSS_STYLES = """
    @page {
        size: A4 portrait;
        margin: 18mm 15mm 20mm 15mm;
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 8pt;
            color: #718096;
        }
    }

    @media print {
        body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        .section-wrapper, .example-wrapper, .practice-wrapper, .callout-wrapper, .diagram-wrapper {
            break-inside: avoid;
            page-break-inside: avoid;
        }
    }

    * {
        box-sizing: border-box;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.55;
        color: #1a202c;
        background-color: #ffffff;
        margin: 0;
        padding: 0;
    }

    /* Header Styling */
    .doc-header {
        border-bottom: 2px solid #2b6cb0;
        padding-bottom: 12px;
        margin-bottom: 18px;
    }
    .doc-title {
        font-size: 20pt;
        font-weight: 700;
        color: #2b6cb0;
        margin: 0 0 6px 0;
        line-height: 1.25;
    }
    .doc-meta {
        font-size: 9pt;
        color: #4a5568;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .meta-badge {
        background-color: #edf2f7;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-primary {
        background-color: #ebf8ff;
        color: #2b6cb0;
    }

    /* Explicit Modular Section Wrappers */
    .section-wrapper {
        margin-bottom: 18px;
        page-break-inside: auto;
    }
    .section-title {
        font-size: 13pt;
        font-weight: 700;
        color: #2d3748;
        border-left: 4px solid #3182ce;
        padding-left: 8px;
        margin: 16px 0 8px 0;
        page-break-after: avoid;
    }
    .section-subheading {
        font-size: 10.5pt;
        font-weight: 700;
        color: #2b6cb0;
        margin: 12px 0 4px 0;
        page-break-after: avoid;
    }
    .section-content {
        margin: 0 0 8px 0;
        text-align: justify;
    }

    /* Paragraphs & Lists */
    p {
        margin: 0 0 8px 0;
    }
    ul, ol {
        margin: 4px 0 10px 20px;
        padding: 0;
    }
    li {
        margin-bottom: 4px;
    }

    /* Math & Equation Styling */
    .equation-wrapper, .math-block {
        display: block;
        margin: 10px auto;
        padding: 8px 14px;
        background-color: #f7fafc;
        border-left: 3px solid #4a5568;
        border-radius: 4px;
        text-align: center;
        page-break-inside: avoid;
    }
    .math-inline {
        font-family: "Cambria Math", "Times New Roman", serif;
        padding: 0 2px;
    }
    .fraction {
        display: inline-flex;
        flex-direction: column;
        vertical-align: middle;
        text-align: center;
        padding: 0 4px;
    }
    .num {
        border-bottom: 1px solid #1a202c;
        padding-bottom: 1px;
    }
    .den {
        padding-top: 1px;
    }
    .radicand {
        border-top: 1px solid #1a202c;
        padding-top: 1px;
        margin-left: 1px;
    }

    /* Chemistry Elements */
    sub, sup {
        font-size: 75%;
        line-height: 0;
        position: relative;
        vertical-align: baseline;
    }
    sup {
        top: -0.5em;
    }
    sub {
        bottom: -0.25em;
    }

    /* Worked Example Wrapper */
    .example-wrapper {
        background-color: #f0fff4;
        border: 1px solid #c6f6d5;
        border-left: 4px solid #38a169;
        border-radius: 4px;
        padding: 10px 12px;
        margin: 12px 0;
        page-break-inside: avoid;
    }
    .example-header {
        font-weight: 700;
        color: #22543d;
        margin-bottom: 6px;
        font-size: 10pt;
    }
    .example-step {
        margin: 4px 0 4px 4px;
        padding-left: 8px;
        border-left: 2px solid #48bb78;
        font-size: 9.5pt;
    }

    /* Callout Box Wrapper */
    .callout-wrapper {
        border-radius: 4px;
        padding: 10px 12px;
        margin: 12px 0;
        page-break-inside: avoid;
    }
    .callout-tip {
        background-color: #ebf8ff;
        border-left: 4px solid #3182ce;
    }
    .callout-warning, .callout-misconception {
        background-color: #fffaf0;
        border-left: 4px solid #dd6b20;
    }
    .callout-title {
        font-weight: 700;
        margin-bottom: 4px;
        font-size: 9.5pt;
    }
    .callout-tip .callout-title { color: #2b6cb0; }
    .callout-warning .callout-title, .callout-misconception .callout-title { color: #c05621; }

    /* Practice Item Wrapper */
    .practice-wrapper {
        background-color: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 10px 0;
        page-break-inside: avoid;
    }
    .practice-question {
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 6px;
    }
    .practice-answer {
        background-color: #ffffff;
        border-left: 3px solid #319795;
        padding: 6px 10px;
        margin-top: 6px;
        font-size: 9.5pt;
    }
    .practice-explanation {
        font-size: 9pt;
        color: #4a5568;
        margin-top: 4px;
    }

    /* Diagram / Visual Wrapper */
    .diagram-wrapper {
        border: 1px solid #e2e8f0;
        background-color: #f8fafc;
        border-radius: 6px;
        padding: 12px;
        margin: 14px 0;
        text-align: center;
        page-break-inside: avoid;
    }
    .diagram-title {
        font-weight: 700;
        font-size: 10pt;
        color: #2b6cb0;
        margin-bottom: 8px;
    }
    .flow-nodes {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }
    .flow-node {
        background-color: #ffffff;
        border: 1.5px solid #3182ce;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 9pt;
        font-weight: 600;
        color: #2d3748;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .flow-arrow {
        color: #4a5568;
        font-size: 12pt;
        font-weight: bold;
    }

    /* Table Wrapper */
    .table-wrapper {
        margin: 14px 0;
        overflow-x: auto;
        page-break-inside: avoid;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 9.5pt;
    }
    th, td {
        border: 1px solid #cbd5e0;
        padding: 6px 10px;
        text-align: left;
    }
    th {
        background-color: #edf2f7;
        font-weight: 700;
        color: #2d3748;
    }
    tr:nth-child(even) {
        background-color: #f7fafc;
    }

    /* Summary / Key Points */
    .key-points-box {
        background-color: #fefcbf;
        border: 1px solid #f6e05e;
        border-radius: 4px;
        padding: 10px 12px;
        margin: 10px 0;
        page-break-inside: avoid;
    }
    .key-points-title {
        font-weight: 700;
        color: #744210;
        margin-bottom: 4px;
    }
    """

    @classmethod
    def build_html(
        cls,
        doc: NotesDocument,
        include_answers: bool = True
    ) -> str:
        """Assembles a student-ready HTML document adhering strictly to print pagination standards."""
        title = html.escape(doc.title or doc.topic)
        topic = html.escape(doc.topic)
        class_level = html.escape(doc.class_level)
        subject = html.escape(doc.subject)
        curriculum = html.escape(doc.curriculum or "Standard")
        diff_str = doc.difficulty.value if hasattr(doc.difficulty, "value") else str(doc.difficulty)
        depth_str = doc.depth.value if hasattr(doc.depth, "value") else str(doc.depth)

        sections_html = []
        for sec in doc.sections:
            sec_html = cls._render_section(sec)
            sections_html.append(sec_html)

        practice_html = ""
        if doc.practice:
            practice_items = []
            for idx, p in enumerate(doc.practice):
                p_item = cls._render_practice_item(p, idx + 1, include_answers)
                practice_items.append(p_item)

            practice_html = f"""
            <div class="section-wrapper practice-section">
                <div class="section-title">Practice & Concept Checkpoints</div>
                {"".join(practice_items)}
            </div>
            """

        visuals_html = ""
        if doc.visuals:
            v_items = []
            for v in doc.visuals:
                v_items.append(cls._render_visual_spec(v))
            visuals_html = f"""
            <div class="section-wrapper visuals-section">
                {"".join(v_items)}
            </div>
            """

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        {cls.CSS_STYLES}
    </style>
</head>
<body>
    <div class="doc-header">
        <div class="doc-title">{title}</div>
        <div class="doc-meta">
            <span class="meta-badge badge-primary">{topic}</span>
            <span class="meta-badge">{class_level}</span>
            <span class="meta-badge">{subject}</span>
            <span class="meta-badge">{curriculum}</span>
            <span class="meta-badge">Difficulty: {diff_str.capitalize()}</span>
            <span class="meta-badge">Depth: {depth_str.capitalize()}</span>
        </div>
    </div>

    {"".join(sections_html)}
    {visuals_html}
    {practice_html}
</body>
</html>
"""
        return full_html

    @classmethod
    def _render_section(cls, sec: NoteSection) -> str:
        """Renders an individual pedagogical section inside an explicit section-wrapper."""
        title_esc = html.escape(sec.title)
        
        # Typeset section content (Math + Chemistry + Markdown)
        raw_paragraphs = [p.strip() for p in sec.content.split("\n\n") if p.strip()]
        paragraphs_html = []
        for p in raw_paragraphs:
            # Detect Markdown tables
            p_lines = [l.strip() for l in p.strip().split("\n") if l.strip()]
            if len(p_lines) >= 2 and "|" in p_lines[0] and ("---" in p_lines[1] or "-|-" in p_lines[1].replace(" ", "")):
                table_html = cls._render_markdown_table(p)
                paragraphs_html.append(table_html)
            elif p.startswith("### ") or p.startswith("## "):
                lines = p.split("\n", 1)
                prefix_len = 4 if p.startswith("### ") else 3
                sub_title = lines[0][prefix_len:].strip()
                sub_title_html = f'<div class="section-subheading">{SemanticTypesetter.typeset_markdown(sub_title)}</div>'
                if len(lines) > 1 and lines[1].strip():
                    body_p = SemanticTypesetter.typeset_markdown(lines[1].strip())
                    paragraphs_html.append(f'{sub_title_html}<p class="section-content">{body_p}</p>')
                else:
                    paragraphs_html.append(sub_title_html)
            else:
                formatted_p = SemanticTypesetter.typeset_markdown(p)
                paragraphs_html.append(f'<p class="section-content">{formatted_p}</p>')

        # Key points box
        key_points_html = ""
        if sec.key_points:
            pts = "".join([f"<li>{SemanticTypesetter.typeset_markdown(pt)}</li>" for pt in sec.key_points])
            key_points_html = f"""
            <div class="key-points-box">
                <div class="key-points-title">Key Takeaways</div>
                <ul>{pts}</ul>
            </div>
            """

        # Worked examples
        examples_html = ""
        if sec.examples:
            ex_cards = []
            for idx, ex in enumerate(sec.examples):
                ex_text = SemanticTypesetter.typeset_markdown(ex)
                if "\n" in ex_text:
                    lines = [l.strip() for l in ex_text.split("\n") if l.strip()]
                    formatted_steps = []
                    for l in lines:
                        if re.match(r'^(?:<strong>)?Step\s*\d+', l, re.IGNORECASE):
                            formatted_steps.append(f'<div class="example-step">{l}</div>')
                        else:
                            formatted_steps.append(f'<div>{l}</div>')
                    ex_text = "".join(formatted_steps)
                ex_cards.append(f"""
                <div class="example-wrapper">
                    <div class="example-header">Worked Example {idx+1}</div>
                    <div class="example-body">{ex_text}</div>
                </div>
                """)
            examples_html = "".join(ex_cards)

        # Callouts
        callouts_html = ""
        if sec.callouts:
            c_cards = []
            for c in sec.callouts:
                c_type = getattr(c, "type", "tip")
                c_title = html.escape(getattr(c, "title", "Note"))
                c_text = SemanticTypesetter.typeset_markdown(getattr(c, "text", ""))
                c_class = f"callout-{c_type}"
                c_cards.append(f"""
                <div class="callout-wrapper {c_class}">
                    <div class="callout-title">{c_title}</div>
                    <div class="callout-text">{c_text}</div>
                </div>
                """)
            callouts_html = "".join(c_cards)

        # Explicit formulas
        formulas_html = ""
        if sec.formulas:
            f_cards = []
            for f in sec.formulas:
                f_formatted = SemanticTypesetter.typeset_formula(f)
                f_cards.append(f"""
                <div class="equation-wrapper">
                    <span class="equation-box">{f_formatted}</span>
                </div>
                """)
            formulas_html = "".join(f_cards)

        # Embedded visual spec
        visual_html = ""
        if sec.visual_spec:
            visual_html = cls._render_visual_spec(sec.visual_spec)

        return f"""
        <div class="section-wrapper" id="{sec.id or sec.section_type}">
            <div class="section-title">{title_esc}</div>
            {"".join(paragraphs_html)}
            {key_points_html}
            {formulas_html}
            {visual_html}
            {examples_html}
            {callouts_html}
        </div>
        """

    @classmethod
    def _render_practice_item(cls, p: Dict[str, Any], number: int, include_answers: bool) -> str:
        """Renders a practice question inside a practice-wrapper."""
        q_text = SemanticTypesetter.typeset_markdown(str(p.get("question", "")))
        ans_text = SemanticTypesetter.typeset_markdown(str(p.get("answer", "")))
        exp_text = SemanticTypesetter.typeset_markdown(str(p.get("explanation", "")))
        diff = html.escape(str(p.get("difficulty", "standard")).capitalize())
        q_type = p.get("type") or p.get("category")
        type_badge = f'<span class="meta-badge badge-primary">{html.escape(str(q_type)).capitalize()}</span> ' if q_type else ''

        answer_block = ""
        if include_answers and ans_text:
            answer_block = f"""
            <div class="practice-answer">
                <strong>Answer Key:</strong> {ans_text}
                {f'<div class="practice-explanation"><strong>Explanation:</strong> {exp_text}</div>' if exp_text else ''}
            </div>
            """

        return f"""
        <div class="practice-wrapper">
            <div class="practice-question">Q{number}. {type_badge}{q_text} <span class="meta-badge">{diff}</span></div>
            {answer_block}
        </div>
        """

    @classmethod
    def _render_visual_spec(cls, v: Any) -> str:
        """Renders a visual diagram spec into clean HTML/CSS."""
        v_title = html.escape(getattr(v, "title", "") or "Process Diagram")
        nodes = getattr(v, "nodes", []) or []
        edges = getattr(v, "edges", []) or []

        if not nodes:
            return ""

        node_elems = []
        for idx, n in enumerate(nodes):
            label = SemanticTypesetter.typeset_markdown(str(n.get("label", f"Step {idx+1}")))
            node_elems.append(f'<div class="flow-node">{label}</div>')
            if idx < len(nodes) - 1:
                node_elems.append('<div class="flow-arrow">→</div>')

        return f"""
        <div class="diagram-wrapper">
            <div class="diagram-title">{v_title}</div>
            <div class="flow-nodes">
                {"".join(node_elems)}
            </div>
        </div>
        """

    @classmethod
    def _render_markdown_table(cls, table_md: str) -> str:
        """Converts Markdown table text into clean HTML table."""
        lines = [line.strip() for line in table_md.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return f"<p>{table_md}</p>"

        headers = [c.strip() for c in lines[0].split("|") if c.strip()]
        rows = []
        for line in lines[2:]:
            cells = [SemanticTypesetter.typeset_markdown(c.strip()) for c in line.split("|") if c.strip()]
            if cells:
                rows.append(cells)

        th_html = "".join([f"<th>{SemanticTypesetter.typeset_markdown(h)}</th>" for h in headers])
        tr_html = []
        for r in rows:
            td_html = "".join([f"<td>{c}</td>" for c in r])
            tr_html.append(f"<tr>{td_html}</tr>")

        return f"""
        <div class="table-wrapper">
            <table>
                <thead><tr>{th_html}</tr></thead>
                <tbody>{"".join(tr_html)}</tbody>
            </table>
        </div>
        """
