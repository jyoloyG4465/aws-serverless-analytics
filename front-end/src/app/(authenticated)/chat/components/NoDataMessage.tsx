/**
 * データがない場合に表示するメッセージコンポーネント
 */

interface NoDataMessageProps {
  message: string;
}

export default function NoDataMessage({ message }: NoDataMessageProps) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex items-start">
          <svg
            className="h-6 w-6 text-amber-400 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div className="ml-4">
            <h3 className="text-lg font-medium text-amber-800">
              データが見つかりません
            </h3>
            <p className="mt-2 text-sm text-amber-700">{message}</p>
            <a
              href="/home"
              className="mt-4 inline-flex items-center px-4 py-2 border border-amber-300 text-sm font-medium rounded-md text-amber-800 bg-amber-100 hover:bg-amber-200 transition-colors"
            >
              ホーム画面でデータをアップロード
              <svg
                className="ml-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
