/**
 * AWS Cognito認証設定とヘルパー関数
 *
 * Amplify v6の新しいAPIを使用
 */

import { Amplify } from "aws-amplify";
import {
  signIn as amplifySignIn,
  signOut as amplifySignOut,
  getCurrentUser,
  fetchAuthSession,
  SignInInput,
} from "aws-amplify/auth";

// Amplify設定
Amplify.configure(
  {
    Auth: {
      Cognito: {
        userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || "",
        userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "",
        loginWith: {
          email: true,
        },
      },
    },
  },
  {
    ssr: true, // Server-Side Rendering対応
  }
);

/**
 * ログイン
 */
export async function login(email: string, password: string) {
  try {
    const input: SignInInput = {
      username: email,
      password,
    };
    const result = await amplifySignIn(input);

    // 初回ログイン時のパスワード変更が必要な場合
    if (
      result.nextStep.signInStep ===
      "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED"
    ) {
      return {
        success: false,
        requirePasswordChange: true,
        message: "初回ログインです。パスワードを変更してください。",
      };
    }

    return {
      success: true,
      message: "ログインに成功しました",
    };
  } catch (error: unknown) {
    console.error("Login error:", error);

    if (error instanceof Error) {
      // エラーメッセージを日本語化
      if (error.message.includes("Incorrect username or password")) {
        return {
          success: false,
          message: "メールアドレスまたはパスワードが正しくありません",
        };
      }
      if (error.message.includes("User does not exist")) {
        return {
          success: false,
          message: "ユーザーが存在しません",
        };
      }
    }

    return {
      success: false,
      message: "ログインに失敗しました",
    };
  }
}

/**
 * ログアウト
 */
export async function logoutFromCognito() {
  try {
    await amplifySignOut();
    return {
      success: true,
      message: "ログアウトしました",
    };
  } catch (error) {
    console.error("Logout error:", error);
    return {
      success: false,
      message: "ログアウトに失敗しました",
    };
  }
}

/**
 * 認証状態をチェック
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    await getCurrentUser();
    return true;
  } catch {
    return false;
  }
}

/**
 * 現在のユーザー情報を取得
 */
export async function getCognitoUserInfo() {
  try {
    const user = await getCurrentUser();
    return {
      success: true,
      user: {
        userId: user.userId,
        username: user.username,
      },
    };
  } catch (error) {
    console.error("Get user error:", error);
    return {
      success: false,
      user: null,
    };
  }
}

/**
 * IDトークンを取得（API呼び出し用）
 */
export async function getIdToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    return idToken || null;
  } catch (error) {
    console.error("Get ID token error:", error);
    return null;
  }
}

/**
 * Cognito User ID（sub）を取得
 */
export async function getUserId(): Promise<string | null> {
  try {
    const user = await getCurrentUser();
    return user.userId; // これがCognito User ID (sub)
  } catch (error) {
    console.error("Get user ID error:", error);
    return null;
  }
}
