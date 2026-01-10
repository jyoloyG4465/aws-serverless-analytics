import { RefObject, useState, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatMessagesProps {
  messages: Message[];
  isLoading: boolean;
  onSampleClick: (question: string) => void;
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

const sampleQuestions = [
  "最もよく見ているチャンネルトップ10は？",
  "全部で何本の動画を見ましたか？",
  "最近1ヶ月の視聴傾向を教えて",
  "日別の視聴数の推移を教えて",
];

// タイプライターフック
function useTypewriter(text: string, speed: number = 15, enabled: boolean = true) {
  const [displayedText, setDisplayedText] = useState(enabled ? "" : text);
  const [isComplete, setIsComplete] = useState(!enabled);

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(text);
      setIsComplete(true);
      return;
    }

    setDisplayedText("");
    setIsComplete(false);
    let index = 0;

    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        clearInterval(timer);
        setIsComplete(true);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed, enabled]);

  return { displayedText, isComplete };
}

// アシスタントメッセージコンポーネント
function AssistantMessage({
  content,
  timestamp,
  isLatest,
}: {
  content: string;
  timestamp: Date;
  isLatest: boolean;
}) {
  const { displayedText } = useTypewriter(content, 15, isLatest);

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-lg px-4 py-3 bg-white text-gray-800 border border-gray-200">
        <p className="text-sm whitespace-pre-wrap">{displayedText}</p>
        <p className="text-xs mt-2 text-gray-500">
          {timestamp.toLocaleTimeString("ja-JP", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

export default function ChatMessages({
  messages,
  isLoading,
  onSampleClick,
  messagesEndRef,
}: ChatMessagesProps) {
  return (
    <>
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
                onClick={() => onSampleClick(question)}
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
          messages.map((message, index) => {
            const isLatestAssistant =
              message.role === "assistant" && index === messages.length - 1;

            if (message.role === "assistant") {
              return (
                <AssistantMessage
                  key={index}
                  content={message.content}
                  timestamp={message.timestamp}
                  isLatest={isLatestAssistant}
                />
              );
            }

            return (
              <div key={index} className="flex justify-end">
                <div className="max-w-[80%] rounded-lg px-4 py-3 bg-blue-600 text-white">
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className="text-xs mt-2 text-blue-100">
                    {message.timestamp.toLocaleTimeString("ja-JP", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            );
          })
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
    </>
  );
}
