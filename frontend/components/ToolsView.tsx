'use client';

import { useState } from 'react';
import { Wrench, Loader2, RefreshCw, Sparkles, FileText } from 'lucide-react';
import { api } from '@/lib/api';

interface ToolsViewProps {
  userId: string;
}

export default function ToolsView({ userId }: ToolsViewProps) {
  const [activeTool, setActiveTool] = useState<'rewrite' | 'rephrase'>('rewrite');
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [tone, setTone] = useState('professional');

  const handleRewrite = async () => {
    if (!input.trim()) return;

    setIsLoading(true);
    setOutput('');

    try {
      const result = await api.rewrite({ user_prompt: input });
      setOutput(result.enhanced_prompt);
    } catch (error) {
      console.error('Error:', error);
      setOutput('Error: Failed to rewrite prompt');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRephrase = async () => {
    if (!input.trim()) return;

    setIsLoading(true);
    setOutput('');

    try {
      const result = await api.rephrase({ text: input, tone });
      setOutput(result.rephrased_text);
    } catch (error) {
      console.error('Error:', error);
      setOutput('Error: Failed to rephrase text');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-6 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2 mb-4">
          <Wrench className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-gray-900">AI Tools</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setActiveTool('rewrite');
              setInput('');
              setOutput('');
            }}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              activeTool === 'rewrite'
                ? 'bg-primary-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            Rewrite Prompt
          </button>
          <button
            onClick={() => {
              setActiveTool('rephrase');
              setInput('');
              setOutput('');
            }}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              activeTool === 'rephrase'
                ? 'bg-primary-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            <RefreshCw className="w-4 h-4" />
            Rephrase Text
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {activeTool === 'rephrase' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tone
              </label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900"
              >
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="formal">Formal</option>
                <option value="friendly">Friendly</option>
                <option value="academic">Academic</option>
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {activeTool === 'rewrite' ? 'Original Prompt' : 'Original Text'}
              </label>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={activeTool === 'rewrite' ? 'Enter prompt to enhance...' : 'Enter text to rephrase...'}
                rows={12}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {activeTool === 'rewrite' ? 'Enhanced Prompt' : 'Rephrased Text'}
              </label>
              <div className="relative">
                <textarea
                  value={output}
                  readOnly
                  placeholder={activeTool === 'rewrite' ? 'Enhanced prompt will appear here...' : 'Rephrased text will appear here...'}
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
              onClick={activeTool === 'rewrite' ? handleRewrite : handleRephrase}
              disabled={isLoading || !input.trim()}
              className="px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  {activeTool === 'rewrite' ? (
                    <Sparkles className="w-5 h-5" />
                  ) : (
                    <RefreshCw className="w-5 h-5" />
                  )}
                  {activeTool === 'rewrite' ? 'Enhance Prompt' : 'Rephrase Text'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

