"use client";

import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "@/lib/api";
import ChatHeader from "./ChatHeader";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";

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
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // メッセージを自動スクロール
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // メッセージ送信
  const handleSendMessage = async (question?: string) => {
    const messageText = question || inputText.trim();

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
    setInputText("");

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
      setError(
        err instanceof Error ? err.message : "メッセージ送信に失敗しました"
      );

      // エラーメッセージを表示
      const errorMessage: Message = {
        role: "assistant",
        content: `エラー: ${
          err instanceof Error ? err.message : "メッセージ送信に失敗しました"
        }`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 会話をクリア
  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <ChatHeader
        showClearButton={messages.length > 0}
        onClear={handleClear}
      />
      <ChatMessages
        messages={messages}
        isLoading={isLoading}
        onSampleClick={handleSendMessage}
        messagesEndRef={messagesEndRef}
      />
      <ChatInput
        inputText={inputText}
        isLoading={isLoading}
        error={error}
        onInputChange={setInputText}
        onSend={() => handleSendMessage()}
      />
    </div>
  );
}
