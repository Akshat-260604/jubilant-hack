'use client';

import { useState, useEffect } from 'react';
import { Languages, Loader2, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api';

interface TranslateViewProps {
  userId: string;
}

export default function TranslateView({ userId }: TranslateViewProps) {
  const [text, setText] = useState('');
  const [targetLang, setTargetLang] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [languages, setLanguages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingLanguages, setIsLoadingLanguages] = useState(true);

  useEffect(() => {
    const fetchLanguages = async () => {
      try {
        const langs = await api.getLanguages();
        setLanguages(langs);
        if (langs.length > 0) {
          setTargetLang(langs[0]);
        }
      } catch (error) {
        console.error('Error fetching languages:', error);
      } finally {
        setIsLoadingLanguages(false);
      }
    };

    fetchLanguages();
  }, []);

  const handleTranslate = async () => {
    if (!text.trim() || !targetLang) return;

    setIsLoading(true);
    setTranslatedText('');

    try {
      const result = await api.translate({
        text,
        target_lang: targetLang,
      });
      setTranslatedText(result.translated_text);
    } catch (error) {
      console.error('Error:', error);
      setTranslatedText('Error: Failed to translate text');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-6 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2 mb-4">
          <Languages className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-gray-900">Translation</h3>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Language
            </label>
            {isLoadingLanguages ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm text-gray-500">Loading languages...</span>
              </div>
            ) : (
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900"
              >
                {languages.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Source Text
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter text to translate..."
                rows={12}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Translated Text
              </label>
              <div className="relative">
                <textarea
                  value={translatedText}
                  readOnly
                  placeholder="Translation will appear here..."
                  rows={12}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 resize-none text-gray-900"
                />
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
                    <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleTranslate}
              disabled={isLoading || !text.trim() || !targetLang}
              className="px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Translating...
                </>
              ) : (
                <>
                  <ArrowRight className="w-5 h-5" />
                  Translate
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

