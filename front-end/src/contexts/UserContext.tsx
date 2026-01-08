"use client";

/**
 * ユーザー情報をアプリ全体で共有するためのContext
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { getCognitoUserInfo, logoutFromCognito } from "@/lib/auth";

interface UserContextType {
  username: string;
  loadingUser: boolean;
  handleLogout: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [username, setUsername] = useState<string>("");
  const [loadingUser, setLoadingUser] = useState(true);

  // ユーザー情報を取得
  useEffect(() => {
    const fetchUserInfo = async () => {
      const result = await getCognitoUserInfo();
      if (result.success && result.user) {
        setUsername(result.user.username);
      }
      setLoadingUser(false);
    };
    fetchUserInfo();
  }, []);

  const handleLogout = async () => {
    const result = await logoutFromCognito();
    if (result.success) {
      router.push("/login");
    }
  };

  return (
    <UserContext.Provider value={{ username, loadingUser, handleLogout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextType {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}
