/**
 * チャットページの説明セクション（フッター）
 */

import Link from "next/link";

export default function ChatDescription() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-2xl mx-auto">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">使い方</h3>
          <div className="space-y-2 text-xs text-gray-600">
            <p>
              アップロードしたYouTube閲覧履歴データについて、AIに質問できます。
            </p>
            <p>Claude 3.5 Sonnetが、あなたの視聴履歴を分析して回答します。</p>
            <p className="text-gray-500">
              注意：データがアップロードされていない場合は、まず
              <Link href="/" className="text-blue-600 hover:underline">
                アップロードページ
              </Link>
              からファイルをアップロードしてください。
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
