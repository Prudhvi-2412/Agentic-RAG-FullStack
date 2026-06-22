import { useState, useRef, useEffect } from 'react';

const BACKEND_URL = (import.meta as any).env.VITE_BACKEND_URL || 
  ((import.meta as any).env.DEV ? 'http://localhost:8000' : 'https://agentic-rag-fullstack-1.onrender.com');

// STT Locale mappings
const STT_LOCALE_MAP: Record<string, string> = {
  de: 'de-DE',
  fr: 'fr-FR',
  es: 'es-ES',
  it: 'it-IT',
  pt: 'pt-PT',
  ta: 'ta-IN',
  te: 'te-IN',
  ml: 'ml-IN',
  kn: 'kn-IN',
  mr: 'mr-IN',
  en: 'en-US'
};

export function useAudio() {
  // TTS Settings & Playback states
  const [ttsLanguage, setTtsLanguage] = useState<string>('en');
  const [ttsGender, setTtsGender] = useState<'female' | 'male'>('female');
  const [ttsRate, setTtsRate] = useState<number>(1.0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState<boolean>(false);
  const [activeSpeechText, setActiveSpeechText] = useState<string | null>(null);

  // STT states
  const [isListening, setIsListening] = useState<boolean>(false);
  const [sttLanguage, setSttLanguage] = useState<string>('en');
  const [sttError, setSttError] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // Play Speech synthesis
  const playTTS = async (text: string, customLang?: string) => {
    // Stop any currently playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    if (isPlaying && activeSpeechText === text) {
      setIsPlaying(false);
      setActiveSpeechText(null);
      return;
    }

    setIsLoadingAudio(true);
    setActiveSpeechText(text);

    try {
      const selectedLang = customLang || ttsLanguage;
      console.log("Sending TTS Request:", { text, language: selectedLang, gender: ttsGender, rate: ttsRate });
      
      const response = await fetch(`${BACKEND_URL}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          language: selectedLang,
          gender: ttsGender,
          rate: ttsRate
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate speech audio stream.');
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.oncanplaythrough = () => {
        setIsLoadingAudio(false);
        setIsPlaying(true);
        audio.play().catch(err => {
          console.error("Playback failed:", err);
          setIsPlaying(false);
        });
      };

      audio.onended = () => {
        setIsPlaying(false);
        setActiveSpeechText(null);
      };

      audio.onerror = (e) => {
        console.error("Audio playback error:", e);
        setIsLoadingAudio(false);
        setIsPlaying(false);
        setActiveSpeechText(null);
      };

      audioRef.current = audio;
    } catch (err: any) {
      console.error(err);
      setIsLoadingAudio(false);
      setIsPlaying(false);
      setActiveSpeechText(null);
      alert(err.message || 'TTS request failed');
    }
  };

  const stopTTS = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(false);
    setActiveSpeechText(null);
  };

  // Toggle Speech Recognition (STT)
  const toggleSpeechToText = (onTranscript: (text: string) => void) => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSttError('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
      alert('Speech recognition is not supported in this browser. Please try Google Chrome.');
      return;
    }

    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    setIsListening(true);
    setSttError(null);

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = STT_LOCALE_MAP[sttLanguage] || 'en-US';

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      if (transcript) {
        onTranscript(transcript);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('STT error:', event.error);
      setSttError(`Error: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  return {
    // TTS States
    ttsLanguage,
    setTtsLanguage,
    ttsGender,
    setTtsGender,
    ttsRate,
    setTtsRate,
    isPlaying,
    isLoadingAudio,
    activeSpeechText,
    playTTS,
    stopTTS,
    
    // STT States
    isListening,
    sttLanguage,
    setSttLanguage,
    sttError,
    toggleSpeechToText
  };
}
