import { useState, useRef, useEffect } from 'react';
import { BACKEND_URL } from '../config';

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
  const audioUrlRef = useRef<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const requestRef = useRef<AbortController | null>(null);

  /** Stops playback and releases the blob URL; without this every narration leaks memory. */
  const releaseAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  // Clean up audio, in-flight requests and recognition on unmount
  useEffect(() => {
    return () => {
      releaseAudio();
      requestRef.current?.abort();
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // Play Speech synthesis
  const playTTS = async (text: string, customLang?: string) => {
    const wasPlayingThisText = isPlaying && activeSpeechText === text;

    // Stop any currently playing audio and cancel a pending synthesis request
    requestRef.current?.abort();
    releaseAudio();

    if (wasPlayingThisText) {
      setIsPlaying(false);
      setIsLoadingAudio(false);
      setActiveSpeechText(null);
      return;
    }

    setIsLoadingAudio(true);
    setActiveSpeechText(text);

    const controller = new AbortController();
    requestRef.current = controller;

    try {
      const selectedLang = customLang || ttsLanguage;

      const response = await fetch(`${BACKEND_URL}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
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
      if (controller.signal.aborted) return;
      if (audioBlob.size === 0) {
        throw new Error('Speech synthesis returned no audio.');
      }

      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      audioUrlRef.current = audioUrl;

      audio.oncanplaythrough = () => {
        setIsLoadingAudio(false);
        setIsPlaying(true);
        audio.play().catch(err => {
          console.error('Playback failed:', err);
          setIsPlaying(false);
          setActiveSpeechText(null);
        });
      };

      audio.onended = () => {
        setIsPlaying(false);
        setActiveSpeechText(null);
        releaseAudio();
      };

      audio.onerror = (e) => {
        console.error('Audio playback error:', e);
        setIsLoadingAudio(false);
        setIsPlaying(false);
        setActiveSpeechText(null);
        releaseAudio();
      };
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      console.error(err);
      setIsLoadingAudio(false);
      setIsPlaying(false);
      setActiveSpeechText(null);
      alert(err.message || 'TTS request failed');
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  };

  const stopTTS = () => {
    requestRef.current?.abort();
    releaseAudio();
    setIsLoadingAudio(false);
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
    try {
      recognition.start();
    } catch (err: any) {
      // start() throws if a previous session is still shutting down; don't strand the
      // microphone button in its "listening" state.
      console.error('Could not start speech recognition:', err);
      setSttError(err?.message || 'Could not start speech recognition.');
      setIsListening(false);
      recognitionRef.current = null;
    }
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
