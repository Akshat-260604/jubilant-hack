'use client';

import { FileText, MessageSquare, FileCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  activeTab: 'chat' | 'reports';
  setActiveTab: (tab: 'chat' | 'reports') => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const menuItems = [
    { id: 'chat' as const, label: 'Chat & Documents', icon: MessageSquare },
    { id: 'reports' as const, label: 'Generate Reports', icon: FileCheck },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col shadow-sm">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <FileText className="w-6 h-6 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900">Healthcare AI</span>
        </div>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                    activeTab === item.id
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
