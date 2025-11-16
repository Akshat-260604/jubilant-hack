'use client';

import { useState, useRef, useEffect } from 'react';
import ChatView from './ChatView';
import SmartChatView from './SmartChatView';
import SearchView from './SearchView';
import TranslateView from './TranslateView';
import ToolsView from './ToolsView';

interface ChatInterfaceProps {
  activeTab: 'chat' | 'smart' | 'search' | 'translate' | 'tools';
}

export default function ChatInterface({ activeTab }: ChatInterfaceProps) {
  const [userId, setUserId] = useState('');
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
      setUserId(savedUserId);
      setIsConfigured(true);
    }
  }, []);

  const handleUserIdSubmit = (id: string) => {
    setUserId(id);
    setIsConfigured(true);
    localStorage.setItem('userId', id);
  };

  if (!isConfigured) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Welcome</h2>
          <p className="text-gray-600 mb-6">Please enter your User ID to continue</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              const id = formData.get('userId') as string;
              if (id.trim()) {
                handleUserIdSubmit(id.trim());
              }
            }}
            className="space-y-4"
          >
            <input
              type="text"
              name="userId"
              placeholder="Enter User ID"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900"
            />
            <button
              type="submit"
              className="w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 transition-colors"
            >
              Continue
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {activeTab === 'chat' && <ChatView userId={userId} />}
      {activeTab === 'smart' && <SmartChatView userId={userId} />}
      {activeTab === 'search' && <SearchView userId={userId} />}
      {activeTab === 'translate' && <TranslateView userId={userId} />}
      {activeTab === 'tools' && <ToolsView userId={userId} />}
    </div>
  );
}

