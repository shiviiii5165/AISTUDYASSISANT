import { useState, useEffect, useRef, useCallback } from "react";

export type VoiceLanguage = "hi-IN" | "en-IN" | "en-US";

export interface UseVoiceInputOptions {
  onTranscript?: (text: string) => void;  // called on every interim result
  onFinal?: (text: string) => void;        // called only when user stops speaking
  language?: VoiceLanguage;
}

export interface UseVoiceInputReturn {
  isListening: boolean;
  isSupported: boolean;
  transcript: string;
  error: string | null;
  language: VoiceLanguage;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
  setLanguage: (lang: VoiceLanguage) => void;
  clearTranscript: () => void;
}

// Extend Window type for browser speech API
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export function useVoiceInput(options: UseVoiceInputOptions = {}): UseVoiceInputReturn {
  const { onTranscript, onFinal, language: initialLang = "hi-IN" } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<VoiceLanguage>(initialLang);

  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef("");

  // Check browser support once
  const isSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  // Build a fresh recognition instance every time language changes
  const buildRecognition = useCallback(() => {
    if (!isSupported) return null;

    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    const rec = new SpeechRecognitionAPI();
    rec.continuous = true;       // keep listening until we stop manually
    rec.interimResults = true;   // show words while still speaking
    rec.lang = language;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      setIsListening(true);
      setError(null);
      finalTranscriptRef.current = "";
    };

    rec.onresult = (event: any) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      // Accumulate finals across multiple utterances
      if (final) {
        finalTranscriptRef.current += final + " ";
      }

      const combined = (finalTranscriptRef.current + interim).trim();
      setTranscript(combined);
      onTranscript?.(combined);
    };

    rec.onend = () => {
      setIsListening(false);
      const lastText = finalTranscriptRef.current.trim();
      if (lastText) {
        onFinal?.(lastText);
      }
    };

    rec.onerror = (event: any) => {
      setIsListening(false);
      const msgs: Record<string, string> = {
        "not-allowed":
          "Microphone access denied. Please allow microphone permission in browser settings.",
        "no-speech": "No speech detected. Please speak clearly.",
        "network": "Network error. Check your internet connection.",
        "audio-capture": "No microphone found on this device.",
        "aborted": "",  // user manually stopped — silent
      };
      const msg = msgs[event.error] ?? `Voice error: ${event.error}`;
      if (msg) setError(msg);
    };

    return rec;
  }, [language, onTranscript, onFinal, isSupported]);

  // Teardown old instance when language changes
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, [language]);

  const startListening = useCallback(() => {
    if (!isSupported) {
      setError(
        "Voice input is not supported in this browser. Please use Chrome or Edge."
      );
      return;
    }

    // Stop any existing session first
    recognitionRef.current?.abort();

    const rec = buildRecognition();
    if (!rec) return;

    recognitionRef.current = rec;
    setTranscript("");
    finalTranscriptRef.current = "";

    try {
      rec.start();
    } catch (e) {
      setError("Could not start voice input. Please try again.");
    }
  }, [buildRecognition, isSupported]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const clearTranscript = useCallback(() => {
    setTranscript("");
    finalTranscriptRef.current = "";
  }, []);

  // Auto-stop on component unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  return {
    isListening,
    isSupported,
    transcript,
    error,
    language,
    startListening,
    stopListening,
    toggleListening,
    setLanguage,
    clearTranscript,
  };
}
