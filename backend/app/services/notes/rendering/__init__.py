"""
TeachGenie Document Rendering Engine
====================================
Transforms structured NotesDocument models into print-accurate,
student-ready HTML and PDF artifacts with semantic mathematical and chemical typesetting.
"""
from .typesetter import SemanticTypesetter
from .html_builder import HTMLNoteBuilder
from .pdf_renderer import PDFNoteRenderer, PDFRenderer

__all__ = [
    "SemanticTypesetter",
    "HTMLNoteBuilder",
    "PDFNoteRenderer",
    "PDFRenderer"
]
