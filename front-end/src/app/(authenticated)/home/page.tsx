/**
 * ホームページ（ファイルアップロード画面）
 * 認証とヘッダーは layout.tsx で適用
 */

import FileUploader from "./components/FileUploader";
import UploadDescription from "./components/UploadDescription";

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <FileUploader />
      <UploadDescription />
    </div>
  );
}
