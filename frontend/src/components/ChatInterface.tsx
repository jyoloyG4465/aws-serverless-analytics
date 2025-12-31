"use client";

import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

/**
 * チャットインターフェース
 *
 * Bedrock (Claude 3.5 Sonnet) を使った YouTube 閲覧履歴の AI 分析
 */
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // メッセージを自動スクロール
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 質問例
  const sampleQuestions = [
    "最もよく見ているチャンネルトップ10は？",
    "全部で何本の動画を見ましたか？",
    "最近1ヶ月の視聴傾向を教えて",
    "日別の視聴数の推移を教えて",
  ];

  // メッセージ送信
  const handleSendMessage = async (question?: string) => {
    const messageText = question || input.trim();

    if (!messageText) {
      return;
    }

    setError(null);
    setIsLoading(true);

    // ユーザーメッセージを追加
    const userMessage: Message = {
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      // チャットAPIを呼び出し
      const response = await sendChatMessage(messageText);

      // AIの回答を追加
      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      setError(err instanceof Error ? err.message : "メッセージ送信に失敗しました");

      // エラーメッセージを表示
      const errorMessage: Message = {
        role: "assistant",
        content: `エラー: ${err instanceof Error ? err.message : "メッセージ送信に失敗しました"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Enter キーで送信
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !isLoading) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 質問例をクリック
  const handleSampleClick = (question: string) => {
    handleSendMessage(question);
  };

  // 会話をクリア
  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      {/* ヘッダー */}
      <div className="flex justify-between items-center mb-4 pb-4 border-b border-gray-200">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">
            YouTube 閲覧履歴分析チャット
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Claude 3.5 Sonnet による AI 分析
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleClear}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            会話をクリア
          </button>
        )}
      </div>

      {/* 質問例（メッセージがない場合のみ表示） */}
      {messages.length === 0 && (
        <div className="mb-6">
          <p className="text-sm font-medium text-gray-700 mb-3">
            質問例をクリックしてください:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sampleQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => handleSampleClick(question)}
                disabled={isLoading}
                className="px-4 py-3 text-left text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* メッセージ一覧 */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 min-h-[400px] max-h-[600px] bg-gray-50 rounded-lg p-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p className="mt-2 text-sm">
                質問を入力するか、質問例をクリックしてください
              </p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-800 border border-gray-200"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p
                  className={`text-xs mt-2 ${
                    message.role === "user" ? "text-blue-100" : "text-gray-500"
                  }`}
                >
                  {message.timestamp.toLocaleTimeString("ja-JP", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))
        )}

        {/* ローディング表示 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 border border-gray-200 rounded-lg px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="animate-bounce">●</div>
                <div className="animate-bounce delay-100">●</div>
                <div className="animate-bounce delay-200">●</div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* エラー表示 */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 入力フォーム */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="質問を入力してください..."
          disabled={isLoading}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={isLoading || !input.trim()}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? "送信中..." : "送信"}
        </button>
      </div>
    </div>
  );
}
