# DynamoDBチャット履歴保存機能 実装計画

## 概要
チャットメッセージをDynamoDBに保存し、ページリロード時に自動復元する機能を実装します。

**要件:**
- 保存方式: メッセージ単位（全メッセージを時系列で保存）
- 保存上限: ユーザーごとに最新50メッセージ
- 削除機能: 不要（自動削除のみ）
- 表示: ページリロード時に過去のメッセージを自動表示

## アーキテクチャ

```
ユーザー → POST /chat → Lambda → DynamoDB保存（ユーザー/AI両方）
                                → Athena + Bedrock処理
                                → 50件超過時に古いメッセージ削除

ページロード → GET /chat/history → Lambda → DynamoDB取得（最新50件）
                                           → フロントエンド表示
```

## DynamoDB テーブル設計

**テーブル名:** `youtube-analytics-chat-history`

**キー:**
- Partition Key: `user_id` (String) - Cognito User ID
- Sort Key: `timestamp` (Number) - Unix timestamp (ミリ秒)

**属性:**
- `message_id` (String, UUID)
- `role` (String): "user" | "assistant"
- `content` (String): メッセージ本文

**課金:** On-Demand（予測不可能なアクセスパターンに適している）

## 実装ステップ

### 1. DynamoDBスタック作成

**新規ファイル:** `cdk/stacks/dynamodb_stack.py`

DynamoDBテーブルを定義:
- テーブル名: `youtube-analytics-chat-history`
- Partition Key: `user_id`, Sort Key: `timestamp`
- On-Demand課金モード
- RemovalPolicy.DESTROY（開発環境用）

### 2. CDK app.py修正

**修正ファイル:** `cdk/app.py`

- `DynamoDBStack`をインポート
- `dynamodb_stack`インスタンス作成
- `lambda_stack`にテーブルを渡す（`chat_history_table=dynamodb_stack.chat_history_table`）
- `lambda_stack.add_dependency(dynamodb_stack)`を追加

### 3. LambdaStack修正

**修正ファイル:** `cdk/stacks/lambda_stack.py`

- コンストラクタに`chat_history_table: dynamodb.ITable`パラメータ追加
- `chat_api_function`の環境変数に`CHAT_HISTORY_TABLE`追加
- `chat_history_table.grant_read_write_data(self.chat_api_function)`で権限付与

### 4. API Gateway修正

**修正ファイル:** `cdk/stacks/api_gateway_stack.py`

`/chat/history` GETエンドポイント追加:
```python
history_resource = chat_resource.add_resource("history")
history_resource.add_method(
    "GET",
    chat_integration,  # 同じLambda関数を使用
    authorizer=self.authorizer,
    authorization_type=apigw.AuthorizationType.COGNITO,
)
```

### 5. DynamoDBクライアント作成

**新規ファイル:** `lambdas/chat_api/shared/dynamodb_client.py`

`ChatHistoryClient`クラス:
- `save_message(user_id, role, content)`: メッセージ保存 + 50件超過時に古いメッセージ削除
- `get_history(user_id, limit=50)`: 履歴取得（古い順にソート）
- エラーハンドリング: DynamoDB障害時もチャット機能は継続（ログのみ）

### 6. Lambda handler修正

**修正ファイル:** `lambdas/chat_api/handler.py`

主な変更:
- `ChatHistoryClient`をインポート
- `CHAT_HISTORY_TABLE`環境変数を追加
- HTTPメソッド（GET/POST）で処理を分岐
- `handle_get_history(user_id)`: 履歴取得処理（新規）
- `handle_chat_message()`: 既存のチャット処理 + ユーザーメッセージとAI回答をDynamoDB保存

### 7. フロントエンド API関数追加

**修正ファイル:** `front-end/src/lib/api.ts`

`getChatHistory()` 関数追加:
```typescript
export async function getChatHistory(): Promise<ChatHistoryResponse> {
  const headers = await getAuthHeaders();
  const response = await axios.get<ChatHistoryResponse>(
    `${API_URL}/chat/history`,
    { headers }
  );
  return response.data;
}
```

**修正ファイル:** `front-end/src/lib/types.ts`

型定義追加:
```typescript
export interface ChatMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  count: number;
}
```

### 8. ChatInterface修正

**修正ファイル:** `front-end/src/components/ChatInterface.tsx`

主な変更:
- `getChatHistory`をインポート
- 初回マウント時に履歴を取得する`useEffect`追加:
  ```typescript
  useEffect(() => {
    const loadChatHistory = async () => {
      const response = await getChatHistory();
      const loadedMessages = response.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.timestamp),
      }));
      setMessages(loadedMessages);
    };
    loadChatHistory();
  }, []);
  ```

## デプロイ手順

```bash
# 1. DynamoDBスタックをデプロイ
cd cdk
source .venv/bin/activate
cdk deploy YoutubeAnalyticsDynamoDBStack

# 2. Lambdaスタックを再デプロイ
cdk deploy YoutubeAnalyticsLambdaStack

# 3. API Gatewayスタックを再デプロイ
cdk deploy YoutubeAnalyticsApiGatewayStack

# 4. フロントエンドをビルド（手動デプロイ）
cd ../front-end
npm run build
```

## テスト観点

1. **基本機能**: メッセージ送信 → DynamoDB保存 → ページリロード → 履歴復元
2. **50件上限**: 51件目送信 → 1件目が自動削除される
3. **マルチユーザー**: 異なるユーザーでログイン → 履歴が分離されている
4. **エラーハンドリング**: DynamoDB障害時もチャット機能は継続動作
5. **パフォーマンス**: 履歴取得が1秒以内

## クリティカルファイル

**新規作成:**
1. `cdk/stacks/dynamodb_stack.py`
2. `lambdas/chat_api/shared/dynamodb_client.py`

**修正:**
3. `cdk/app.py`
4. `cdk/stacks/lambda_stack.py`
5. `cdk/stacks/api_gateway_stack.py`
6. `lambdas/chat_api/handler.py`
7. `front-end/src/lib/api.ts`
8. `front-end/src/lib/types.ts`
9. `front-end/src/components/ChatInterface.tsx`

## コスト見積もり

**DynamoDB On-Demand:**
- 月間100往復想定: 約$0.28/月（無料枠内）
