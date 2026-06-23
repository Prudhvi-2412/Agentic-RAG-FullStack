import React from 'react';
import { VolumeX, Mic, Settings, Sliders, ChevronDown } from 'lucide-react';

export const LANGUAGES = [
  { code: 'en', name: 'English (US)', flag: '🇺🇸' },
  { code: 'de', name: 'German (Deutsch)', flag: '🇩🇪' },
  { code: 'fr', name: 'French (Français)', flag: '🇫🇷' },
  { code: 'es', name: 'Spanish (Español)', flag: '🇪🇸' },
  { code: 'it', name: 'Italian (Italiano)', flag: '🇮🇹' },
  { code: 'pt', name: 'Portuguese (Português)', flag: '🇵🇹' },
  { code: 'ta', name: 'Tamil (தமிழ்)', flag: '🇮🇳' },
  { code: 'te', name: 'Telugu (తెలుగు)', flag: '🇮🇳' },
  { code: 'ml', name: 'Malayalam (മലയാളம்)', flag: '🇮🇳' },
  { code: 'kn', name: 'Kannada (ಕನ್ನಡ)', flag: '🇮🇳' },
  { code: 'mr', name: 'Marathi (मराठी)', flag: '🇮🇳' }
];

interface VoiceControllerProps {
  ttsLanguage: string;
  setTtsLanguage: (lang: string) => void;
  ttsGender: 'female' | 'male';
  setTtsGender: (gender: 'female' | 'male') => void;
  ttsRate: number;
  setTtsRate: (rate: number) => void;
  isPlaying: boolean;
  stopTTS: () => void;
  isListening: boolean;
  sttLanguage: string;
  setSttLanguage: (lang: string) => void;
}

export const VoiceController: React.FC<VoiceControllerProps> = ({
  ttsLanguage,
  setTtsLanguage,
  ttsGender,
  setTtsGender,
  ttsRate,
  setTtsRate,
  isPlaying,
  stopTTS,
  isListening,
  sttLanguage,
  setSttLanguage
}) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState<'tts' | 'stt'>('tts');

  const currentSttLang = LANGUAGES.find(l => l.code === sttLanguage) || LANGUAGES[0];

  return (
    <div className="relative">
      {/* Floating Status Indicator / Settings Toggle */}
      <div className="flex items-center gap-2">
        {isPlaying && (
          <button
            onClick={stopTTS}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50 hover:bg-rose-500/20 active:scale-95 transition-all"
            title="Stop audio narration"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            </span>
            <span>Stop Narration</span>
            <VolumeX className="h-3.5 w-3.5" />
          </button>
        )}
        
        {isListening && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/50 animate-pulse">
            <Mic className="h-3.5 w-3.5 animate-bounce" />
            <span>Listening ({currentSttLang.name})...</span>
          </div>
        )}

        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all border shadow-sm ${
            isOpen 
              ? 'bg-blue-600 border-blue-600 text-white shadow-blue-500/10'
              : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
          }`}
        >
          <Settings className="h-3.5 w-3.5" />
          <span>Voice Controls</span>
          <ChevronDown className={`h-3 w-3 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Popover Settings Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2.5 w-72 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl shadow-xl z-50 p-4 animate-in fade-in slide-in-from-top-3 duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm flex items-center gap-1.5">
              <Sliders className="h-4 w-4 text-blue-500" />
              Voice Settings
            </h4>
            <span className="text-[10px] text-slate-400 font-medium">Neural synthesis scale</span>
          </div>

          {/* Mode Tabs */}
          <div className="flex border-b border-slate-100 dark:border-slate-800 my-2">
            <button
              onClick={() => setActiveTab('tts')}
              className={`flex-1 py-1.5 text-xs font-bold border-b-2 text-center transition-all ${
                activeTab === 'tts' 
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
              }`}
            >
              Speech Output (TTS)
            </button>
            <button
              onClick={() => setActiveTab('stt')}
              className={`flex-1 py-1.5 text-xs font-bold border-b-2 text-center transition-all ${
                activeTab === 'stt' 
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
              }`}
            >
              Voice Input (STT)
            </button>
          </div>

          {activeTab === 'tts' ? (
            /* TTS Settings */
            <div className="flex flex-col gap-3.5 pt-1.5">
              {/* Language Selection */}
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Synthesis Language</label>
                <div className="relative mt-1">
                  <select
                    value={ttsLanguage}
                    onChange={(e) => setTtsLanguage(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500"
                  >
                    {LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {lang.flag} {lang.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Voice Gender Selection */}
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Voice Profile</label>
                <div className="flex gap-2 mt-1">
                  <button
                    onClick={() => setTtsGender('female')}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                      ttsGender === 'female'
                        ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800'
                        : 'bg-slate-50 dark:bg-slate-950 text-slate-500 border-slate-200 dark:border-slate-800 hover:bg-slate-100'
                    }`}
                  >
                    Female Model
                  </button>
                  <button
                    onClick={() => setTtsGender('male')}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                      ttsGender === 'male'
                        ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800'
                        : 'bg-slate-50 dark:bg-slate-950 text-slate-500 border-slate-200 dark:border-slate-800 hover:bg-slate-100'
                    }`}
                  >
                    Male Model
                  </button>
                </div>
              </div>

              {/* Rate control */}
              <div>
                <div className="flex justify-between items-center">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Speech Rate (Speed)</label>
                  <span className="text-[10px] font-semibold text-blue-500">{ttsRate}x</span>
                </div>
                <input
                  type="range"
                  min="0.8"
                  max="1.5"
                  step="0.1"
                  value={ttsRate}
                  onChange={(e) => setTtsRate(parseFloat(e.target.value))}
                  className="w-full mt-1.5 accent-blue-500 cursor-pointer h-1 bg-slate-100 dark:bg-slate-800 rounded-lg appearance-none"
                />
              </div>
            </div>
          ) : (
            /* STT Settings */
            <div className="flex flex-col gap-3.5 pt-1.5">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Listening Language</label>
                <div className="relative mt-1">
                  <select
                    value={sttLanguage}
                    onChange={(e) => setSttLanguage(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:border-blue-500"
                  >
                    {LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {lang.flag} {lang.name}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="text-[10px] text-slate-400 mt-2 leading-relaxed">
                  Make sure this matches the language you speak. The web recognition engine converts it instantly to text.
                </p>
              </div>
            </div>
          )}

          {/* Quick status */}
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[9px] font-bold text-slate-400 dark:text-slate-500">
            <span>Synthesis: edge-tts</span>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          </div>
        </div>
      )}
    </div>
  );
};
