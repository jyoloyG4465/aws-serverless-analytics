"use client";

/**
 * チャットページ（AI分析画面）
 * 認証とヘッダーは layout.tsx で適用
 */

import { useState, useEffect } from "react";
import { checkDataStatus } from "@/lib/api";
import ChatInterface from "./components/ChatInterface";
import ChatDescription from "./components/ChatDescription";
import NoDataMessage from "./components/NoDataMessage";

export default function ChatPage() {
  const [hasData, setHasData] = useState<boolean | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await checkDataStatus();
        setHasData(status.hasData);
        setStatusMessage(status.message);
      } catch (err) {
        console.error("Data status check error:", err);
        setHasData(false);
        setStatusMessage(
          err instanceof Error
            ? err.message
            : "データステータスの確認に失敗しました"
        );
      }
    };

    checkStatus();
  }, []);

  // チェック中
  if (hasData === null) {
    return (
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">データを確認中...</p>
          </div>
        </div>
      </div>
    );
  }

  // データなし
  if (!hasData) {
    return (
      <>
        <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
          <NoDataMessage message={statusMessage} />
        </div>
        <ChatDescription />
      </>
    );
  }

  // データあり
  return (
    <>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
        <ChatInterface />
      </div>
      <ChatDescription />
    </>
  );
}
