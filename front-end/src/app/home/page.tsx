"use client";

/**
 * ホームページ（ファイルアップロード画面）
 * 認証が必要
 */

import AuthGuard from "@/app/shared/components/AuthGuard";
import Header from "@/app/shared/components/Header";
import FileUploader from "./components/FileUploader";
import UploadDescription from "./components/UploadDescription";

function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      {/* メインコンテンツ */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <FileUploader />
        <UploadDescription />
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
