'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, FileText, ExternalLink, AlertCircle, CheckCircle } from 'lucide-react';

interface Citation {
  document_id: string;
  document_name?: string;
  chunk_text?: string;
  page_number?: number;
  source_type?: 'uploaded' | 'google_drive';
  google_drive_link?: string;
  score?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: Citation[];
  noAnswerFound?: boolean;
}

interface HealthcareChatProps {
  userId: string;
}

export default function HealthcareChat({ userId }: HealthcareChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [contextId, setContextId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      // TODO: Replace with actual API call
      // For now, simulate response with citations
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Simulate streaming response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        citations: [],
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Simulate streaming
      const responseText = `Based on the medical documents provided, I can help you with information about ${currentInput}. The data shows relevant findings from the uploaded documents.`;
      const words = responseText.split(' ');
      
      for (let i = 0; i < words.length; i++) {
        await new Promise((resolve) => setTimeout(resolve, 50));
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg.role === 'assistant') {
            lastMsg.content = words.slice(0, i + 1).join(' ') + (i < words.length - 1 ? '' : '');
            // Add sample citations
            if (i === words.length - 1) {
              lastMsg.citations = [
                {
                  document_id: 'doc_123',
                  document_name: 'Patient_Report_2024.pdf',
                  chunk_text: 'Relevant excerpt from document...',
                  page_number: 5,
                  source_type: 'uploaded',
                  score: 0.92,
                },
                {
                  document_id: 'drive_456',
                  document_name: 'Clinical_Data.xlsx',
                  chunk_text: 'Data from spreadsheet...',
                  source_type: 'google_drive',
                  google_drive_link: 'https://drive.google.com/file/d/123/view',
                  score: 0.87,
                },
              ];
            }
          }
          return updated;
        });
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: 'Sorry, an error occurred. Please try again.',
        timestamp: new Date(),
        noAnswerFound: false,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">Chat with Medical Documents</h3>
            <p className="text-sm text-gray-600">
              Ask questions about your uploaded documents and Google Drive files
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-12">
            <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <p className="text-lg mb-2">Start a conversation</p>
            <p className="text-sm">Ask questions about your medical documents</p>
            <div className="mt-6 max-w-md mx-auto">
              <p className="text-xs text-gray-500 mb-2">Example questions:</p>
              <div className="space-y-1 text-left">
                <p className="text-sm text-gray-600">• "What are the key findings in the patient report?"</p>
                <p className="text-sm text-gray-600">• "Summarize the clinical data from the documents"</p>
                <p className="text-sm text-gray-600">• "What medications are mentioned in the files?"</p>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-3xl ${message.role === 'user' ? 'flex flex-col items-end' : ''}`}>
              <div
                className={`rounded-lg px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>

              {/* Citations */}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-3 space-y-2 w-full">
                  <p className="text-xs font-semibold text-gray-600 mb-2">Sources & Citations:</p>
                  {message.citations.map((citation, idx) => (
                    <div
                      key={idx}
                      className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-blue-600" />
                          <span className="font-medium text-gray-900">
                            {citation.document_name || citation.document_id}
                          </span>
                          {citation.source_type === 'google_drive' && (
                            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                              Google Drive
                            </span>
                          )}
                        </div>
                        {citation.google_drive_link && (
                          <a
                            href={citation.google_drive_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-blue-600 hover:text-blue-700"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span className="text-xs">Open</span>
                          </a>
                        )}
                      </div>
                      {citation.chunk_text && (
                        <p className="text-gray-600 text-xs mt-1 italic">
                          "{citation.chunk_text.substring(0, 150)}..."
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        {citation.page_number && <span>Page {citation.page_number}</span>}
                        {citation.score && (
                          <span>Relevance: {(citation.score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* No Answer Found */}
              {message.noAnswerFound && (
                <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-yellow-800">
                      Information Not Available
                    </p>
                    <p className="text-xs text-yellow-700 mt-1">
                      The requested information could not be found in any of the provided documents.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-gray-600" />
              <span className="text-sm text-gray-600">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your medical documents..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 text-gray-900"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

