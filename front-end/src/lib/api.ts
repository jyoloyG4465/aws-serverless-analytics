/**
 * API呼び出しヘルパー関数
 */

import axios, { AxiosError } from "axios";
import { getIdToken } from "./auth";
import type {
  UploadUrlResponse,
  ChatRequest,
  ChatResponse,
  ErrorResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * 認証ヘッダーを取得
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getIdToken();
  if (!token) {
    throw new Error("認証トークンが取得できませんでした");
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

/**
 * S3署名付きURLを取得
 */
export async function getUploadUrl(
  fileName: string
): Promise<UploadUrlResponse> {
  try {
    const headers = await getAuthHeaders();
    const response = await axios.post<UploadUrlResponse>(
      `${API_URL}/upload`,
      { fileName }, // POSTリクエストのbodyとして送信
      { headers }
    );
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response) {
      const errorData = error.response.data as ErrorResponse;
      throw new Error(errorData.error || "アップロードURL取得に失敗しました");
    }
    throw new Error("アップロードURL取得に失敗しました");
  }
}

/**
 * S3に直接ファイルをアップロード
 */
export async function uploadToS3(
  presignedUrl: string,
  file: File
): Promise<void> {
  try {
    await axios.put(presignedUrl, file, {
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch {
    throw new Error("S3へのアップロードに失敗しました");
  }
}

/**
 * チャットAPIにメッセージを送信
 */
export async function sendChatMessage(question: string): Promise<ChatResponse> {
  try {
    const headers = await getAuthHeaders();
    const request: ChatRequest = { question };
    const response = await axios.post<ChatResponse>(
      `${API_URL}/chat`,
      request,
      { headers }
    );
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response) {
      const errorData = error.response.data as ErrorResponse;
      throw new Error(errorData.error || "メッセージ送信に失敗しました");
    }
    throw new Error("メッセージ送信に失敗しました");
  }
}
