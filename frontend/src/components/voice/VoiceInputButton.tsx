import { useState, useEffect } from "react";
import { useVoiceInput } from "../../hooks/useVoiceInput";
import type { VoiceLanguage } from "../../hooks/useVoiceInput";

interface VoiceInputButtonProps {
  onResult: (text: string) => void;       // fires when user finishes speaking
  onInterim?: (text: string) => void;     // fires while user is still speaking
  disabled?: boolean;
  className?: string;
}

const LANGUAGES: { code: VoiceLanguage; label: string; flag: string }[] = [
  { code: "hi-IN", label: "हिं", flag: "Hindi" },
  { code: "en-IN", label: "EN", flag: "English" },
];

export default function VoiceInputButton({
  onResult,
  onInterim,
  disabled = false,
  className = "",
}: VoiceInputButtonProps) {
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [pulseCount, setPulseCount] = useState(0);

  const {
    isListening,
    isSupported,
    transcript,
    error,
    language,
    toggleListening,
    setLanguage,
    clearTranscript,
  } = useVoiceInput({
    onFinal: (text) => {
      onResult(text);
      clearTranscript();
    },
    onTranscript: (text) => {
      onInterim?.(text);
    },
  });

  // Pulse animation counter while listening
  useEffect(() => {
    if (!isListening) return;
    const interval = setInterval(() => {
      setPulseCount((c) => c + 1);
    }, 600);
    return () => clearInterval(interval);
  }, [isListening]);

  if (!isSupported) return null; // silently hide on unsupported browsers

  const handleMicClick = () => {
    if (disabled) return;
    setShowLangMenu(false);
    toggleListening();
  };

  const handleLangSelect = (lang: VoiceLanguage) => {
    setLanguage(lang);
    setShowLangMenu(false);
  };

  const currentLang = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0];

  return (
    <div className={className} style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: "4px" }}>

      {/* Language toggle pill — only shown when not listening */}
      {!isListening && (
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setShowLangMenu((v) => !v)}
            disabled={disabled}
            title="Switch language"
            style={{
              fontSize: "11px",
              fontWeight: 500,
              padding: "4px 8px",
              borderRadius: "20px",
              border: "0.5px solid #d1d5db",
              background: "transparent",
              color: "#6b7280",
              cursor: disabled ? "not-allowed" : "pointer",
              lineHeight: 1,
              letterSpacing: "0.02em",
            }}
          >
            {currentLang.label}
          </button>

          {/* Dropdown */}
          {showLangMenu && (
            <div
              style={{
                position: "absolute",
                bottom: "calc(100% + 6px)",
                left: 0,
                background: "white",
                border: "0.5px solid #e5e7eb",
                borderRadius: "10px",
                padding: "4px",
                zIndex: 50,
                minWidth: "110px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              }}
            >
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => handleLangSelect(lang.code)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    width: "100%",
                    padding: "7px 10px",
                    borderRadius: "7px",
                    border: "none",
                    background: lang.code === language ? "#f0fdf4" : "transparent",
                    color: lang.code === language ? "#15803d" : "#374151",
                    fontSize: "13px",
                    cursor: "pointer",
                    fontWeight: lang.code === language ? 500 : 400,
                    textAlign: "left",
                  }}
                >
                  <span style={{ fontSize: "15px", fontWeight: 500 }}>{lang.label}</span>
                  <span>{lang.flag}</span>
                  {lang.code === language && (
                    <span style={{ marginLeft: "auto", fontSize: "12px", color: "#15803d" }}>✓</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Mic Button */}
      <button
        onClick={handleMicClick}
        disabled={disabled}
        aria-label={isListening ? "Stop voice input" : "Start voice input"}
        title={isListening ? "Tap to stop" : `Speak in ${currentLang.flag}`}
        style={{
          width: "38px",
          height: "38px",
          borderRadius: "50%",
          border: isListening ? "2px solid #16a34a" : "0.5px solid #d1d5db",
          background: isListening ? "#f0fdf4" : "transparent",
          color: isListening ? "#16a34a" : "#6b7280",
          cursor: disabled ? "not-allowed" : "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "all 0.2s ease",
          flexShrink: 0,
        }}
      >
        {isListening ? (
          /* Animated bars when recording */
          <SoundWaveIcon pulseCount={pulseCount} />
        ) : (
          /* Static mic icon */
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" x2="12" y1="19" y2="22"/>
          </svg>
        )}
      </button>

      {/* Live transcript preview bubble */}
      {isListening && transcript && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            right: 0,
            background: "white",
            border: "0.5px solid #e5e7eb",
            borderRadius: "12px",
            padding: "8px 12px",
            fontSize: "13px",
            color: "#374151",
            maxWidth: "260px",
            zIndex: 40,
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          <span style={{ color: "#16a34a", fontSize: "11px", display: "block", marginBottom: "3px", fontWeight: 500 }}>
            Listening...
          </span>
          {transcript}
        </div>
      )}

      {/* Error toast */}
      {error && !isListening && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            right: 0,
            background: "#fef2f2",
            border: "0.5px solid #fca5a5",
            borderRadius: "10px",
            padding: "8px 12px",
            fontSize: "12px",
            color: "#991b1b",
            maxWidth: "240px",
            zIndex: 40,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}

/* Animated sound wave icon shown while recording */
function SoundWaveIcon({ pulseCount }: { pulseCount: number }) {
  const heights = [
    [4, 10, 6],
    [6, 14, 8],
    [10, 6, 12],
    [8, 12, 4],
  ];
  const frame = pulseCount % heights.length;
  const [h1, h2, h3] = heights[frame];

  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
      <rect x="2" y={9 - h1 / 2} width="3" height={h1} rx="1.5" style={{ transition: "all 0.2s ease" }} />
      <rect x="7" y={9 - h2 / 2} width="3" height={h2} rx="1.5" style={{ transition: "all 0.2s ease" }} />
      <rect x="12" y={9 - h3 / 2} width="3" height={h3} rx="1.5" style={{ transition: "all 0.2s ease" }} />
    </svg>
  );
}
