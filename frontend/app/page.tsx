'use client';

import { useState, useEffect } from 'react';
import UnifiedChatInterface from '@/components/UnifiedChatInterface';
import ReportGenerator from '@/components/ReportGenerator';
import Sidebar from '@/components/Sidebar';
import { FileText, MessageSquare, FileCheck, Activity } from 'lucide-react';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'reports'>('chat');
  const [userId] = useState(() => {
    // Get userId from localStorage or use default
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('userId');
      if (saved) return saved;
      // Set default userId if none exists
      const defaultUserId = 'user_' + Date.now();
      localStorage.setItem('userId', defaultUserId);
      return defaultUserId;
    }
    return 'default_user';
  });

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Healthcare AI Assistant</h1>
              <p className="text-sm text-gray-500">Manage medical documents and generate insights</p>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>User ID: {userId}</span>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && <UnifiedChatInterface userId={userId} />}
          {activeTab === 'reports' && <ReportGenerator userId={userId} />}
        </div>
      </main>
    </div>
  );
}
