"use client";

/**
 * ファイルアップロードコンポーネント
 * YouTube履歴JSONファイルをS3にアップロード
 */

import { useState, ChangeEvent, FormEvent } from "react";
import { getUploadUrl, uploadToS3 } from "@/lib/api";

export default function FileUploader() {
  const [selectedFile, updateSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState({
    uploading: false,
    progress: 0,
    message: "",
    error: "",
  });

  // アップロード状態を一括更新
  const updateUploadState = (updates: Partial<typeof uploadState>) => {
    setUploadState((prev) => ({ ...prev, ...updates }));
  };

  // バリデーション関数: YouTube履歴JSONの形式チェック
  // JSON配列であること、1つ目のレコードにtitle/timeキーが存在することを確認
  const validateYouTubeHistoryJson = async (file: File): Promise<boolean> => {
    try {
      const text = await file.text();
      const data = JSON.parse(text); // JSONパースエラーはcatchで拾う
      const firstRecord = data[0]; // 配列でない、または空配列の場合はエラー

      return "title" in firstRecord && "time" in firstRecord;
    } catch {
      return false;
    }
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 1. 拡張子チェック
    if (!file.name.endsWith(".json")) {
      updateUploadState({ error: "JSONファイルのみアップロード可能です" });
      return;
    }

    // 2. バリデーション実行（ローディング表示）
    try {
      updateUploadState({ message: "ファイルを検証中..." });

      const isValid = await validateYouTubeHistoryJson(file);

      if (!isValid) {
        updateUploadState({
          error: "有効なJSON形式ではありません",
          message: "",
        });
        return;
      }

      // 検証成功
      updateSelectedFile(file);
      updateUploadState({ error: "", message: "" });
    } catch {
      updateUploadState({
        error: "ファイルの検証中にエラーが発生しました",
        message: "",
      });
    }
  };

  const handleUpload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedFile) {
      updateUploadState({ error: "ファイルを選択してください" });
      return;
    }

    updateUploadState({ uploading: true, progress: 0, error: "", message: "" });

    try {
      // 1. 署名付きURLを取得
      updateUploadState({
        progress: 25,
        message: "アップロードURLを取得中...",
      });
      const uploadData = await getUploadUrl(selectedFile.name);

      // 2. S3に直接アップロード
      updateUploadState({
        progress: 50,
        message: "ファイルをアップロード中...",
      });
      await uploadToS3(uploadData.uploadUrl, selectedFile);

      // 3. 完了
      updateUploadState({
        progress: 100,
        message: `アップロード完了しました。データ処理が開始されます。\nS3パス: ${uploadData.key}`,
      });

      // フォームをリセット
      updateSelectedFile(null);
      const fileInput = document.getElementById(
        "file-upload"
      ) as HTMLInputElement;
      if (fileInput) {
        fileInput.value = "";
      }
    } catch (err) {
      console.error("Upload error:", err);
      updateUploadState({
        error:
          err instanceof Error ? err.message : "アップロードに失敗しました",
        progress: 0,
      });
    } finally {
      updateUploadState({ uploading: false });
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
          <li>Google TakeoutのYouTube履歴JSONファイルを選択</li>
          <li>アップロードボタンをクリック</li>
          <li>データ処理が自動的に開始されます（数分かかる場合があります）</li>
        </ol>
      </div>

      {/* デモデータダウンロードセクション */}
      <div className="mb-6 p-4 bg-indigo-50 rounded-md border border-indigo-100">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-indigo-800">
              デモ用サンプルデータ
            </h3>
            <p className="text-sm text-indigo-600 mt-1">
              YouTube履歴のサンプルJSONファイルをダウンロードできます
            </p>
          </div>
          <a
            href="/youtube-history-sample.json"
            download="youtube-history-sample.json"
            className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            <svg
              className="mr-2 h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            ダウンロード
          </a>
        </div>
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
            disabled={uploadState.uploading}
            className="block w-full text-sm text-gray-900 border border-gray-300 rounded-md cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          {selectedFile && (
            <p className="mt-2 text-sm text-gray-600">
              選択されたファイル: {selectedFile.name} (
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        {uploadState.uploading && (
          <div className="space-y-2">
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${uploadState.progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-600 text-center">
              {uploadState.message}
            </p>
          </div>
        )}

        {uploadState.error && (
          <div className="rounded-md bg-red-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  {uploadState.error}
                </h3>
              </div>
            </div>
          </div>
        )}

        {uploadState.message && !uploadState.uploading && (
          <div className="rounded-md bg-green-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800 whitespace-pre-line">
                  {uploadState.message}
                </h3>
              </div>
            </div>
          </div>
        )}

        <div>
          <button
            type="submit"
            disabled={!selectedFile || uploadState.uploading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {uploadState.uploading ? (
              <span className="flex items-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                アップロード中...
              </span>
            ) : (
              "アップロード"
            )}
          </button>
        </div>
      </form>

      <div className="mt-6 p-4 bg-gray-50 rounded-md">
        <h3 className="text-sm font-medium text-gray-700 mb-2">注意事項</h3>
        <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
          <li>
            データは開発者のAWS環境で処理されます。個人情報の取り扱いにご注意ください
          </li>
          <li>JSON配列形式のファイルのみアップロード可能です</li>
          <li>アップロードされたデータは2日後に自動削除されます</li>
          <li>データはユーザーごとに完全に分離されています</li>
        </ul>
      </div>
    </div>
  );
}
