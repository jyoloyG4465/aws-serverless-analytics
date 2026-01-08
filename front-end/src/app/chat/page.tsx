'use client';

/**
 * チャットページ（AI分析画面）
 * 認証が必要
 */

import AuthGuard from '@/components/AuthGuard';
import Header from '@/components/Header';
import ChatInterface from '@/components/ChatInterface';
import ChatDescription from '@/components/ChatDescription';

function ChatPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      {/* メインコンテンツ */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ChatInterface />
      </main>

      <ChatDescription />
    </div>
  );
}

export default function Chat() {
  return (
    <AuthGuard>
      <ChatPage />
    </AuthGuard>
  );
}
