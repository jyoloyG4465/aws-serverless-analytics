"use client";

/**
 * アプリケーション共通ヘッダー
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@/contexts/UserContext";

export default function Header() {
  const pathname = usePathname();
  const { username, loadingUser, handleLogout } = useUser();

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-bold text-gray-900">
            YouTube Analytics
          </h1>
          <nav className="flex gap-4">
            <Link
              href="/home"
              className={`text-sm font-medium ${
                pathname === "/home"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900 transition-colors"
              }`}
            >
              アップロード
            </Link>
            <Link
              href="/chat"
              className={`text-sm font-medium ${
                pathname === "/chat"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900 transition-colors"
              }`}
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
  );
}
