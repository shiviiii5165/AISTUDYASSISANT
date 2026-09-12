# VIDEO COST BREAKDOWN: INFERENCE-ONLY VS. TOTAL PRODUCTION

## 1. Executive Forensic Reconstruction

The previous audit claimed that an educational video in TeachGenie costs **~$0.0018** per video.
This claim was **PARTIALLY VERIFIED**:
- The **$0.0018** figure represents strictly the **INFERENCE-ONLY API COST** when generating a storyboard on a small Flash model.
- It **completely omitted server compute, FFmpeg CPU time, storage, and egress bandwidth**.

Below is the forensic reconstruction of both cost accounting models for a standard 4-scene (60-second) 720p educational video.

---

## 2. Component-by-Component Cost Breakdown

| Component | Provider / Technology | Cost Calculation Method | Inference-Only Cost ($) | Total System Cost ($) |
| :--- | :--- | :--- | :--- | :--- |
| **Storyboard Generation** | Gemini 2.5 Flash (`router.py`) | 1,200 input tokens @ $0.15/M + 750 output tokens @ $0.60/M | **$0.000630** | **$0.000630** |
| **Scene Diagram Prompting**| Pure Python SVG Templates | Deterministic SVG code generation (`graphics/`) | **$0.000000** | **$0.000000** |
| **Voiceover Narration (TTS)**| `edge-tts` / `gTTS` | Free public endpoints with local caching (`tts_service.py`) | **$0.000000** | **$0.000000** |
| **Stock Visual Media** | Pexels REST API | Free API key tier (200 requests/hour) | **$0.000000** | **$0.000000** |
| **FFmpeg Video Encoding** | Local CPU (H.264 / AAC) | ~18s of 100% CPU on Render 0.5 CPU container ($7/mo instance) | *$0.000000 (Ignored)* | **$0.000720** |
| **Temporary Scratch I/O** | Local SSD / Tempdir | 15MB disk write & cleanup (`tempfile`) | *$0.000000 (Ignored)* | **$0.000050** |
| **Artifact Storage** | Supabase Storage Bucket | 12MB MP4 stored for 30 days ($0.021/GB/mo) | *$0.000000 (Ignored)* | **$0.000252** |
| **Egress Bandwidth** | CDN / Supabase Egress | 12MB client download ($0.09/GB) | *$0.000000 (Ignored)* | **$0.001080** |
| **Sub-Total** | | | **$0.000630** | **$0.002732** |
| **With 15% Retry Margin** | | Network retry on stock image or audio chunk | **$0.000725** | **$0.003142** |

---

## 3. Findings & Truth Disclosures

1. **Inference-Only API Cost**:
   - When generating a brand-new storyboard from scratch on Gemini 2.5 Flash: **~$0.0007 per video**.
   - When converting from an existing TeachMe session (`build_storyboard_from_teach_me_state`): **$0.000000 (ZERO LLM tokens)**.
   - If using the current broken default (`openai/gpt-4o` on OpenRouter): **~$0.0105 per video** (15x cost leak).
2. **Total Production & Delivery Cost**:
   - Real-world production, including server CPU time, storage, and egress bandwidth, costs **~$0.0031 per 60-second video**.
3. **Comparison Against Commercial Video AI**:
   - Sora / Runway Gen-3 / HeyGen API: **$0.50 to $3.00 per minute**.
   - TeachGenie's deterministic compositor is **99.4% cheaper** than generative video APIs while guaranteeing exact mathematical formulas and zero visual hallucination.
