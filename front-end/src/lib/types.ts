/**
 * アプリケーション全体で使用する型定義
 */

// 認証関連
export interface AuthResult {
  success: boolean;
  message: string;
  requirePasswordChange?: boolean;
}

export interface UserInfo {
  userId: string;
  username: string;
}

export interface UserResult {
  success: boolean;
  user: UserInfo | null;
}

// API関連
export interface UploadUrlResponse {
  uploadUrl: string;
  key: string;
  bucket: string;
  expiresIn: number;
  message: string;
}

export interface ChatRequest {
  question: string;
}

export interface ChatResponse {
  answer: string;
}

// エラーレスポンス
export interface ErrorResponse {
  error: string;
  details?: string;
}

// データステータス関連
export interface DataStatusResponse {
  hasData: boolean;
  message: string;
}
