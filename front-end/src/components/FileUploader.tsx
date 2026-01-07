'use client';

/**
 * ファイルアップロードコンポーネント
 * YouTube履歴JSONファイルをS3にアップロード
 */

import { useState, ChangeEvent, FormEvent } from 'react';
import { getUploadUrl, uploadToS3 } from '@/lib/api';

export default function FileUploader() {
  const [selectedFile, updateSelectedFile] = useState<File | null>(null);
  const [uploading, updateUploadingStatus] = useState(false);
  const [progress, updateUploadProgress] = useState(0);
  const [message, updateStatusMessage] = useState('');
  const [error, updateErrorMessage] = useState('');

  // ヘルパー関数: メッセージをクリア
  const clearMessages = () => {
    updateErrorMessage('');
    updateStatusMessage('');
  };

  // ヘルパー関数: アップロード開始時の初期化
  const initializeUpload = () => {
    updateUploadingStatus(true);
    updateUploadProgress(0);
    clearMessages();
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // watch-history.jsonのみ受け付ける
      if (selectedFile.name !== 'watch-history.json') {
        updateErrorMessage('watch-history.json のみアップロード可能です');
        updateSelectedFile(null);
        return;
      }

      updateSelectedFile(selectedFile);
      clearMessages();
    }
  };

  const handleUpload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedFile) {
      updateErrorMessage('ファイルを選択してください');
      return;
    }

    initializeUpload();

    try {
      // 1. 署名付きURLを取得
      updateUploadProgress(25);
      updateStatusMessage('アップロードURLを取得中...');
      const uploadData = await getUploadUrl(selectedFile.name);

      // 2. S3に直接アップロード
      updateUploadProgress(50);
      updateStatusMessage('ファイルをアップロード中...');
      await uploadToS3(uploadData.uploadUrl, selectedFile);

      // 3. 完了
      updateUploadProgress(100);
      updateStatusMessage(`アップロード完了しました。データ処理が開始されます。\nS3パス: ${uploadData.key}`);

      // フォームをリセット
      updateSelectedFile(null);
      const fileInput = document.getElementById('file-upload') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }
    } catch (err) {
      console.error('Upload error:', err);
      updateErrorMessage(err instanceof Error ? err.message : 'アップロードに失敗しました');
      updateUploadProgress(0);
    } finally {
      updateUploadingStatus(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        YouTube履歴アップロード
      </h2>

      <div className="mb-6 p-4 bg-blue-50 rounded-md">
        <h3 className="text-sm font-medium text-blue-800 mb-2">使い方</h3>
        <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
          <li>Google Takeoutから取得した watch-history.json を選択</li>
          <li>アップロードボタンをクリック</li>
          <li>データ処理が自動的に開始されます（数分かかる場合があります）</li>
        </ol>
      </div>

      <form onSubmit={handleUpload} className="space-y-4">
        <div>
          <label
            htmlFor="file-upload"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            ファイルを選択
          </label>
          <input
            id="file-upload"
            name="file-upload"
            type="file"
            accept=".json"
            onChange={handleFileChange}
            disabled={uploading}
            className="block w-full text-sm text-gray-900 border border-gray-300 rounded-md cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          {selectedFile && (
            <p className="mt-2 text-sm text-gray-600">
              選択されたファイル: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        {uploading && (
          <div className="space-y-2">
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-600 text-center">{message}</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">{error}</h3>
              </div>
            </div>
          </div>
        )}

        {message && !uploading && (
          <div className="rounded-md bg-green-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800 whitespace-pre-line">{message}</h3>
              </div>
            </div>
          </div>
        )}

        <div>
          <button
            type="submit"
            disabled={!selectedFile || uploading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                アップロード中...
              </span>
            ) : (
              'アップロード'
            )}
          </button>
        </div>
      </form>

      <div className="mt-6 p-4 bg-gray-50 rounded-md">
        <h3 className="text-sm font-medium text-gray-700 mb-2">注意事項</h3>
        <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
          <li>watch-history.json のみアップロード可能です</li>
          <li>アップロードされたデータは2日後に自動削除されます</li>
          <li>データはユーザーごとに完全に分離されています</li>
        </ul>
      </div>
    </div>
  );
}
