interface ChatHeaderProps {
  showClearButton: boolean;
  onClear: () => void;
}

export default function ChatHeader({ showClearButton, onClear }: ChatHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-4 pb-4 border-b border-gray-200">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">
          YouTube 閲覧履歴分析チャット
        </h2>
      </div>
      {showClearButton && (
        <button
          onClick={onClear}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          会話をクリア
        </button>
      )}
    </div>
  );
}
