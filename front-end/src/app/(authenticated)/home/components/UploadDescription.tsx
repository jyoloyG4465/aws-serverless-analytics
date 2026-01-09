/**
 * アップロードページの説明セクション
 */

export default function UploadDescription() {
  return (
    <div className="mt-8 max-w-2xl mx-auto">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          このアプリについて
        </h2>
        <div className="space-y-3 text-sm text-gray-600">
          <p>
            YouTube閲覧履歴（Google Takeout形式）をアップロードすると、
            自動的にデータが処理され、Athenaで分析可能な形式に変換されます。
          </p>
          <p>処理フロー：</p>
          <ol className="list-decimal list-inside space-y-1 ml-4">
            <li>JSONファイルをS3にアップロード</li>
            <li>AWS Glueジョブが自動的に起動</li>
            <li>データがParquet形式に変換されてS3に保存</li>
            <li>Athenaでクエリ可能な状態になります</li>
          </ol>
          <p className="text-xs text-gray-500 mt-4">
            注意：アップロードされたデータは2日後に自動削除されます（検証用途）
          </p>
        </div>
      </div>
    </div>
  );
}
