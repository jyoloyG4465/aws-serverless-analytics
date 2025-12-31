'use client';

/**
 * チャットページ（AI分析画面）
 * 認証が必要
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import AuthGuard from '@/components/AuthGuard';
import ChatInterface from '@/components/ChatInterface';
import { logout, getUser } from '@/lib/auth';

function ChatPage() {
  const router = useRouter();
  const [username, setUsername] = useState<string>('');
  const [loadingUser, setLoadingUser] = useState(true);

  // ユーザー情報を取得
  useState(() => {
    const fetchUser = async () => {
      const result = await getUser();
      if (result.success && result.user) {
        setUsername(result.user.username);
      }
      setLoadingUser(false);
    };
    fetchUser();
  });

  const handleLogout = async () => {
    const result = await logout();
    if (result.success) {
      router.push('/login');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* ヘッダー */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <h1 className="text-2xl font-bold text-gray-900">
              YouTube Analytics
            </h1>
            <nav className="flex gap-4">
              <Link
                href="/"
                className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                アップロード
              </Link>
              <Link
                href="/chat"
                className="text-sm font-medium text-blue-600 border-b-2 border-blue-600"
              >
                チャット分析
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            {!loadingUser && username && (
              <span className="text-sm text-gray-600">
                ログイン中: {username}
              </span>
            )}
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              ログアウト
            </button>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ChatInterface />
      </main>

      {/* フッター（説明） */}
      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="max-w-2xl mx-auto">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              使い方
            </h3>
            <div className="space-y-2 text-xs text-gray-600">
              <p>
                アップロードしたYouTube閲覧履歴データについて、AIに質問できます。
              </p>
              <p>
                Claude 3.5 Sonnetが、あなたの視聴履歴を分析して回答します。
              </p>
              <p className="text-gray-500">
                注意：データがアップロードされていない場合は、まず<Link href="/" className="text-blue-600 hover:underline">アップロードページ</Link>からファイルをアップロードしてください。
              </p>
            </div>
          </div>
        </div>
      </footer>
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
