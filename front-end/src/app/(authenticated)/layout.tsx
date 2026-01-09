"use client";

/**
 * 認証済みページ用レイアウト
 * AuthGuard と Header を共通化
 */

import AuthGuard from "@/app/shared/components/AuthGuard";
import Header from "@/app/shared/components/Header";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
      </div>
    </AuthGuard>
  );
}
