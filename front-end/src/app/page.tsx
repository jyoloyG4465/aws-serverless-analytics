/**
 * ルートページ
 * /home へリダイレクト
 */

import { redirect } from 'next/navigation';

export default function RootPage() {
  redirect('/home');
}
