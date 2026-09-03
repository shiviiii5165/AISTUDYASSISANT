/**
 * TeachGenie Asset Manifest
 * =========================
 * Single source of truth for all image/illustration paths.
 * All paths are relative to /public — served statically by Vite.
 *
 * Generation prompts are co-located so a designer or AI image tool
 * can regenerate each asset from one place.
 *
 * MISSING FILES: The app handles missing images gracefully via the
 * `safeImg` helper below. Drop generated files into /public at the
 * paths listed here and they will appear automatically.
 *
 * Palette to respect in all generated assets:
 *   Deep blue   #3368A0  — primary
 *   Teal-blue   #66A3BF  — secondary
 *   Pale sage   #C8DFDB  — light surface
 *   Warm cream  #F2EFE7  — background
 *   Muted gold  #D4A85F  — accent highlight
 */

// ── Genie character assets ──────────────────────────────────────────────────
// These are the animated AI mascot variants. Each represents a distinct
// emotional/contextual state. All should share the same character design.
//
// Character design brief:
//   A friendly genie mascot in academic/scholar style. Warm-toned skin,
//   flowing deep-blue robes with gold trim, a scholar's lamp that glows
//   with soft amber light. Expressive face — large, friendly eyes. Modern
//   flat-illustration style with subtle gradients. Transparent PNG.
//   The character should feel approachable, not intimidating; educational
//   but playful. Avoid stereotypical Middle-Eastern depictions.

export const GENIE = {
  /** Default standing pose — calm, ready */
  default: '/assets/genie-default.png',
  /** Reading/studying — finger on chin, book open */
  thinking: '/assets/genie/genie-thinking.png',
  /** Arms raised, gold sparkles, big smile — quiz correct / generation done */
  celebrating: '/assets/genie/genie-celebrating.png',
  /** Pointing at an invisible board/screen — TeachMe & lesson context */
  teaching: '/assets/genie/genie-teaching.png',
  /** Welcoming wave — auth, onboarding, first visit */
  welcome: '/assets/genie/genie-welcome.png',
} as const;

export const GENIE_PROMPTS: Record<keyof typeof GENIE, string> = {
  default:
    'A friendly scholar genie mascot standing in a relaxed, confident pose. ' +
    'Deep-blue academic robes with gold-trim details, holding a softly glowing ' +
    'amber lamp. Large expressive eyes, warm smile. Flat modern illustration ' +
    'style, subtle gradient shading. Transparent PNG background. ' +
    'Palette: deep blue #3368A0, gold #D4A85F, warm cream highlights.',

  thinking:
    'Scholar genie mascot in a thoughtful thinking pose: one finger gently ' +
    'touching chin, head tilted slightly, eyes looking upward as if pondering. ' +
    'A small open book floats nearby. Soft glow from the lamp. Same character ' +
    'design as default pose — deep-blue robes, gold trim, friendly face. ' +
    'Flat modern illustration, transparent PNG.',

  celebrating:
    'Scholar genie mascot in a joyful celebration pose: arms raised in a V, ' +
    'big smile, gold sparkles and stars bursting outward around the character. ' +
    'The lamp glows brightly amber. Energetic, dynamic posture conveys success ' +
    'and accomplishment. Same character design. Flat illustration, transparent PNG.',

  teaching:
    'Scholar genie mascot in a teaching stance: one hand raised and pointing ' +
    'forward as if at a whiteboard, other hand holding an open book or scroll. ' +
    'Authoritative but warm posture. Academic setting feel. Same character design ' +
    '— deep blue robes, gold trim. Flat illustration, transparent PNG.',

  welcome:
    'Scholar genie mascot in a warm welcoming pose: one hand raised in a friendly ' +
    'wave, slight forward lean, bright inviting smile. The lamp trails a subtle ' +
    'swirl of golden smoke. Conveys "Welcome, I am here to help." Same character ' +
    'design. Flat illustration, transparent PNG.',
};

// ── Feature illustrations ───────────────────────────────────────────────────
// Supporting illustrations for empty states, feature intros, and section art.
// Style: flat illustration, consistent with TeachGenie palette, no photos.
// All transparent PNGs unless noted.

export const ILLUSTRATIONS = {
  /** Empty library — shown when user has no PDFs uploaded */
  emptyLibrary: '/assets/empty-library.png',
  /** Empty chat — shown before user starts a conversation */
  emptyChat: '/assets/illustrations/empty-chat.png',
  /** Quiz complete celebration screen */
  quizComplete: '/assets/illustrations/quiz-complete.png',
  /** PPT/deck being generated — in-progress state */
  pptGenerating: '/assets/illustrations/ppt-generating.png',
  /** TeachMe page intro / hero area */
  teachMe: '/assets/illustrations/teach-me.png',
  /** Auth page side panel — decorative */
  authSide: '/assets/illustrations/auth-side.png',
  /** Support page hero */
  support: '/assets/illustrations/support-hero.png',
  /** Lesson planner feature */
  lessonPlan: '/assets/illustrations/lesson-plan.png',
} as const;

export const ILLUSTRATION_PROMPTS: Record<keyof typeof ILLUSTRATIONS, string> = {
  emptyLibrary:
    'Flat illustration of a friendly empty bookshelf with a small glowing lamp ' +
    'sitting on the lowest shelf. Muted warm-cream background (#F2EFE7), pale-sage ' +
    'accents (#C8DFDB), deep-blue outlines (#3368A0). The shelf has subtle dust ' +
    'motes. Conveys "your library is empty — add your first document." ' +
    'No text. Square format 512×512.',

  emptyChat:
    'Flat illustration of a speech bubble with a small glowing lamp inside it, ' +
    'surrounded by soft floating question marks and small sparkles. Warm-cream ' +
    'background, deep-blue (#3368A0) and teal-blue (#66A3BF) tones. ' +
    'Conveys "ask your first question." No text. Square format 512×512.',

  quizComplete:
    'Flat celebratory illustration: a trophy with a glowing lamp on top, ' +
    'surrounded by stars, confetti ribbons in deep blue and gold (#D4A85F), ' +
    'and small firework bursts. Warm-cream background. Conveys quiz success. ' +
    'No text. Square format 512×512.',

  pptGenerating:
    'Flat illustration of a presentation slide coming out of a magic lamp with ' +
    'golden smoke trails. Small floating slide thumbnails orbit around it. ' +
    'Deep blue and teal-blue palette, warm cream background. Conveys AI is ' +
    'generating slides. No text. Square format 512×512.',

  teachMe:
    'Flat illustration of a classroom chalkboard with floating mathematical and ' +
    'language symbols (π, Σ, A, B, C) orbiting around it. A glowing lamp sits ' +
    'on the teacher\'s desk in front. Warm academic feel. Deep blue, teal, and ' +
    'gold palette on warm-cream background. No text. Landscape 800×500.',

  authSide:
    'Flat illustration panel showing a stack of floating open books, a glowing ' +
    'lamp, and stars/sparkles suggesting magic and knowledge. Deep blue tones ' +
    '(#3368A0, #66A3BF) on a pale-sage background (#C8DFDB). No characters, ' +
    'no text. Tall portrait format 600×800.',

  support:
    'Flat illustration of two speech bubbles — one with a question mark, one with ' +
    'a checkmark/lightbulb — connected by a subtle line. A small friendly hand ' +
    'waves nearby. Deep blue and teal palette, warm cream background. ' +
    'Conveys "we are here to help." No text. Landscape 800×400.',

  lessonPlan:
    'Flat illustration of a structured timeline or flow diagram emerging from an ' +
    'open book, with small icons representing different learning activities ' +
    '(video, quiz, reading) connected by arrows. Deep blue, teal, gold palette ' +
    'on warm cream. Academic, organized feel. No text. Landscape 800×500.',
};

// ── Landing page assets ──────────────────────────────────────────────────────
// Hero and bento-card images for the public marketing page.
// These benefit from richer, more atmospheric treatment than UI illustrations.

export const LANDING = {
  /** Full-width hero section visual */
  hero: '/assets/hero.png',
  /** Bento card — AI chat/tutoring feature */
  bentoChat: '/assets/bento-chat.png',
  /** Bento card — Quiz engine feature */
  bentoQuiz: '/assets/bento-quiz.png',
  /** Bento card — Presentation deck feature */
  bentoPpt: '/assets/bento-ppt.png',
} as const;

export const LANDING_PROMPTS: Record<keyof typeof LANDING, string> = {
  hero:
    'A dynamic flat illustration of a student\'s desk seen from a 3/4 angle: ' +
    'an open laptop showing a glowing chat interface, stacked textbooks, a ' +
    'glowing magic lamp, floating question-and-answer speech bubbles, and ' +
    'small sparkles. Deep blue (#3368A0) and teal (#66A3BF) tones with warm ' +
    'cream and gold accents. Modern, clean, academic feel. No text. ' +
    'Wide landscape format 1600×900.',

  bentoChat:
    'Flat illustration for an "AI Tutor Chat" feature card: a friendly chat ' +
    'interface with a glowing avatar bubble on one side and a student\'s message ' +
    'bubble on the other, surrounded by small knowledge symbols. Deep blue and ' +
    'teal palette. Square format 600×600.',

  bentoQuiz:
    'Flat illustration for a "Quiz Engine" feature card: a multiple-choice quiz ' +
    'sheet with one option highlighted in gold, surrounded by small trophy and ' +
    'star icons. Deep blue and gold palette on pale sage background. ' +
    'Square format 600×600.',

  bentoPpt:
    'Flat illustration for a "Presentation Deck" feature card: three overlapping ' +
    'slide thumbnails fanning out like a deck of cards, each with simple content ' +
    'icons (chart, bullet points, image). Deep blue and teal palette. ' +
    'Square format 600×600.',
};

// ── Graceful image loading ──────────────────────────────────────────────────
/**
 * Returns img props that hide the element if the src fails to load.
 * Use this for every asset that may not yet exist on disk.
 *
 * Example:
 *   <img {...safeImg(ILLUSTRATIONS.emptyChat)} alt="..." className="..." />
 */
export function safeImg(src: string): { src: string; onError: React.EventHandler<React.SyntheticEvent<HTMLImageElement>> } {
  return {
    src,
    onError: (e: React.SyntheticEvent<HTMLImageElement>) => {
      (e.currentTarget as HTMLImageElement).style.display = 'none';
    },
  };
}

// Re-export React type so callers don't need a separate import for the type
import type React from 'react';
