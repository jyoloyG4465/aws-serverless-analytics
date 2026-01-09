/**
 * チャットページ（AI分析画面）
 * 認証とヘッダーは layout.tsx で適用
 */

import ChatInterface from "./components/ChatInterface";
import ChatDescription from "./components/ChatDescription";

export default function ChatPage() {
  return (
    <>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
        <ChatInterface />
      </div>
      <ChatDescription />
    </>
  );
}
