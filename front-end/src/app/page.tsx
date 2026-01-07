'use client';

/**
 * ホームページ（ファイルアップロード画面）
 * 認証が必要
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import AuthGuard from '@/components/AuthGuard';
import FileUpload from '@/components/FileUpload';
import { logout, getUser } from '@/lib/auth';

function HomePage() {
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
    <div className="min-h-screen bg-gray-50">
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
                className="text-sm font-medium text-blue-600 border-b-2 border-blue-600"
              >
                アップロード
              </Link>
              <Link
                href="/chat"
                className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
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
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <FileUpload />

        {/* 説明セクション */}
        <div className="mt-8 max-w-2xl mx-auto">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              このアプリについて
            </h2>
            <div className="space-y-3 text-sm text-gray-600">
              <p>
                YouTube閲覧履歴（Google Takeout形式）をアップロードすると、
                自動的にデータが処理され、Athenaで分析可能な形式に変換されます。
              </p>
              <p>
                処理フロー：
              </p>
              <ol className="list-decimal list-inside space-y-1 ml-4">
                <li>JSONファイルをS3にアップロード</li>
                <li>AWS Glueジョブが自動的に起動</li>
                <li>データがParquet形式に変換されてS3に保存</li>
                <li>Athenaでクエリ可能な状態になります</li>
              </ol>
              <p className="text-xs text-gray-500 mt-4">
                注意：アップロードされたデータは2日後に自動削除されます（検証用途）
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <AuthGuard>
      <HomePage />
    </AuthGuard>
  );
}
