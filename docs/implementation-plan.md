# YouTube閲覧履歴分析 - AWS サーバーレスアプリケーション実装プラン

## 概要

YouTube閲覧履歴（JSON）をAWSで分析し、Bedrockを使ったチャットインターフェースで質問できるアプリケーションを構築します。

**主要機能**:
- AWS Cognito による認証機能（自分用 + 共有サンプル用の2アカウント）
- **ユーザーごとのデータ完全分離**（S3パスで各ユーザーのデータを分離）
- JSONファイルアップロード → 自動データ加工（Glue Python Shell）
- Athenaでのデータクエリ（ユーザー自身のデータのみアクセス）
- Bedrockチャット（Claude 3.5 Sonnet）によるAI分析
- **期間限定保存**（2日後に自動削除、検証用）

**コスト最適化優先**：個人利用・デモ用として月額$3-5程度を想定

**データ管理ポリシー**:
- ユーザーごとにS3パスを分離（`s3://bucket/{user-id}/`）
- 各ユーザーは自分のデータのみアクセス可能（Cognito User IDで制御）
- アップロード後2日で自動削除（S3ライフサイクルポリシー）
- デモ・検証用途でシンプルな構成

## システムアーキテクチャ

```
[ユーザー] → [Next.js on Amplify]
              ↓ アップロード
           [S3 raw-data]
              ↓ S3イベント
           [Lambda trigger] → [Glue Python Shell]
                                ↓ 加工・Parquet化
                             [S3 processed-data]
                                ↓ クエリ
                             [Athena]

[チャット質問] → [API Gateway] → [Lambda chat-api]
                                   ↓ データ取得
                                [Athena]
                                   ↓ AI分析
                                [Bedrock Claude 3.5]
                                   ↓ 回答
                              [ユーザー]
```

## 技術スタック

- **フロントエンド**: Next.js 14 (App Router) + React + TypeScript + Tailwind CSS
- **バックエンド**: Python 3.9+ (Lambda関数)
- **インフラ**: AWS CDK (Python)
- **AWS サービス**:
  - S3 (ストレージ)
  - Glue Python Shell (データ加工) ← **Redshift不使用でコスト削減**
  - Athena (クエリエンジン)
  - Lambda (サーバーレス関数)
  - Bedrock Claude 3.5 Sonnet (AI分析)
  - API Gateway (REST API)
  - Amplify (フロントエンドホスティング)
  - Cognito (ユーザー認証) ← **追加**
  - IAM (アクセス管理)

## プロジェクト構造（モノレポ）

```
aws-serverless-analytics/
├── README.md
├── .gitignore
├── .env.example
│
├── cdk/                            # AWS CDK (Python)
│   ├── app.py                      # CDKアプリエントリーポイント
│   ├── requirements.txt
│   ├── cdk.json
│   └── stacks/
│       ├── __init__.py
│       ├── storage_stack.py        # S3バケット
│       ├── glue_stack.py           # Glueジョブ
│       ├── lambda_stack.py         # Lambda関数
│       ├── cognito_stack.py        # Cognito ユーザープール（追加）
│       ├── api_stack.py            # API Gateway + Cognito認証
│       ├── athena_stack.py         # Athena設定
│       └── amplify_stack.py        # Amplify Hosting
│
├── lambdas/                        # Lambda関数 (Python)
│   ├── shared/                     # 共通ライブラリ
│   │   ├── __init__.py
│   │   ├── athena_client.py        # Athenaクライアント + キャッシング
│   │   └── bedrock_client.py       # Bedrockクライアント
│   ├── trigger_glue/               # S3イベントトリガー
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── chat_api/                   # チャットAPI
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── upload_presigned/           # 署名付きURL生成
│       ├── handler.py
│       └── requirements.txt
│
├── glue_jobs/                      # Glue Python Shellスクリプト
│   ├── process_youtube_history.py  # データ加工メイン処理
│   ├── requirements.txt            # pandas, pyarrow
│   └── test_local.py               # ローカルテスト用
│
├── frontend/                       # Next.js フロントエンド
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # ホーム（アップロード画面）
│   │   │   ├── login/
│   │   │   │   └── page.tsx        # ログイン画面（追加）
│   │   │   └── chat/
│   │   │       └── page.tsx        # チャット画面
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── LoginForm.tsx       # ログインフォーム（追加）
│   │   │   └── AuthGuard.tsx       # 認証ガード（追加）
│   │   └── lib/
│   │       ├── api.ts              # API呼び出し
│   │       ├── auth.ts             # Cognito認証ヘルパー（追加）
│   │       └── types.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
│
└── docs/
    ├── architecture.md             # アーキテクチャ詳細
    └── deployment.md               # デプロイ手順
```

## 実装の優先順位

### 🔥 優先実装（データパイプライン構築）

**目的**: ファイルアップロード → Glue加工 → Athena までの基本パイプラインを完成させる

1. ✅ **Phase 3.1**: Glueジョブ実装（JSON → Parquet変換）
2. ✅ **Phase 3.2**: Lambda trigger-glue実装（S3イベントでGlue起動）
3. ✅ **Phase 4.4**: Lambda upload-presigned実装（署名付きURL生成）
4. ✅ **Phase 5.1**: Next.jsプロジェクト初期化
5. ✅ **Phase 5.2**: Cognito認証設定
6. ✅ **Phase 5.3**: ログインフォーム作成
7. ✅ **Phase 5.4**: 認証ガード作成
8. ✅ **Phase 5.5**: ファイルアップロードコンポーネント作成
9. ✅ **Phase 5.7**: ページ構成（login, home）
10. **Phase 6.1**: CDKデプロイ実行
11. **Phase 6.2**: Cognitoユーザー作成
12. **Phase 6.3**: フロントエンドデプロイ
13. **Phase 6.4**: 基本動作テスト（アップロード→Glue→Athenaテーブル確認）

### 🔄 後回し（AI/チャット機能）

**目的**: データパイプライン完成後に実装

- **Phase 4.1**: 共通ライブラリ - Athenaクライアント実装
- **Phase 4.2**: 共通ライブラリ - Bedrockクライアント実装
- **Phase 4.3**: Lambda chat-api実装（Athena + Bedrock統合）
- **Phase 5.6**: チャットインターフェースコンポーネント作成
- **Phase 5.7**: チャットページ構成

## 実装ステップ

### Phase 1: プロジェクト初期化 ✅

**ファイル**: プロジェクトルート

1. プロジェクト構造作成
2. `.gitignore` 設定 (`.env`, `cdk.out/`, `node_modules/`, `__pycache__/`, `.DS_Store`)
3. `.env.example` 作成（AWS_REGION, AWS_ACCOUNT_ID など）
4. `README.md` 更新

### Phase 2: AWS CDK インフラストラクチャ構築 ✅

#### 2.1 S3バケット (`cdk/stacks/storage_stack.py`) ✅

3つのバケットを作成（**ユーザーごとのパス分離**）：

1. **raw-data-bucket**: JSONファイルアップロード先
   - パス構造: `s3://bucket/raw/{user-id}/{filename}.json`
   - バージョニング: 無効（デモ用）
   - **ライフサイクル: 2日後に全データ自動削除**
   - S3イベント通知設定（Lambda trigger起動）
   - 例: `s3://raw-bucket/raw/user-abc123/watch-history.json`

2. **processed-data-bucket**: Parquet形式の加工済みデータ
   - パス構造: `s3://bucket/processed/{user-id}/year=YYYY/month=MM/day=DD/data.parquet`
   - パーティション: ユーザーID + 日付
   - 圧縮: Snappy
   - **ライフサイクル: 2日後に全データ自動削除**
   - 例: `s3://processed-bucket/processed/user-abc123/year=2025/month=01/day=15/data.parquet`

3. **athena-results-bucket**: Athenaクエリ結果
   - パス構造: `s3://bucket/results/{user-id}/`
   - **ライフサイクル: 2日後削除**（検証用）

**重要な設計判断**:
- 各ユーザーのデータは完全に分離されたパスに保存
- Lambda関数でCognito User IDを取得してパス生成
- Athenaクエリ時も`user_id`でフィルタリング
- 2日間の期間限定保存でストレージコスト削減（検証用）

#### 2.2 Glue Python Shellジョブ (`cdk/stacks/glue_stack.py`) ✅

**重要な選択**: Glue Python Shellを使用（PySpark不使用）
- 理由: データ量が少量（数MB〜数十MB）のため、Python Shellの方がコスト効率が良い
- DPU: 1.0 (最小)
- タイムアウト: 10分
- Python: 3.9

設定：
```python
glue.CfnJob(
    command=glue.CfnJob.JobCommandProperty(
        name="pythonshell",  # ← PySpark不使用
        python_version="3.9",
        script_location="s3://..."
    ),
    max_capacity=1.0,  # 1 DPU
    timeout=10
)
```

#### 2.3 Athenaワークグループ (`cdk/stacks/athena_stack.py`) ✅

- データベース: `youtube_analytics_db`
- テーブル: `youtube_watch_history`
- **Partition Projection有効**（ユーザーID + 日付でパフォーマンス向上）
- クエリ結果の再利用: 有効（コスト削減）

テーブルスキーマ（**user_idパーティション追加**）：
```sql
CREATE EXTERNAL TABLE youtube_watch_history (
  title STRING,
  video_id STRING,
  channel_name STRING,
  channel_id STRING,
  watched_at TIMESTAMP
)
PARTITIONED BY (
  user_id STRING,
  year INT,
  month INT,
  day INT
)
STORED AS PARQUET
LOCATION 's3://processed-data-bucket/processed/'
TBLPROPERTIES (
  'parquet.compression'='SNAPPY',
  'projection.enabled'='true',
  'projection.user_id.type'='injected',
  'projection.year.type'='integer',
  'projection.year.range'='2020,2030',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.day.type'='integer',
  'projection.day.range'='1,31',
  'storage.location.template'='s3://processed-data-bucket/processed/${user_id}/year=${year}/month=${month}/day=${day}/'
);
```

**クエリ例**（ユーザー自身のデータのみ取得）:
```sql
-- Lambda関数内でuser_idを動的に挿入
SELECT channel_name, COUNT(*) as watch_count
FROM youtube_watch_history
WHERE user_id = 'user-abc123'  -- Cognito User IDから取得
GROUP BY channel_name
ORDER BY watch_count DESC
LIMIT 10;
```

#### 2.4 Lambda関数 (`cdk/stacks/lambda_stack.py`) ✅

3つのLambda関数（**全てCognito User ID対応**）：

1. **trigger-glue**: S3イベント → Glueジョブ起動
   - メモリ: 128MB
   - タイムアウト: 30秒
   - 機能: S3パスからuser_idを抽出してGlueジョブに渡す

2. **chat-api**: Athena + Bedrock統合
   - メモリ: 512MB（Bedrockレスポンス処理のため）
   - タイムアウト: 29秒（API Gateway制限）
   - 環境変数: ATHENA_DATABASE, BEDROCK_MODEL_ID
   - **重要**: API GatewayからCognito User IDを取得し、Athenaクエリに使用

3. **upload-presigned**: S3署名付きURL生成
   - メモリ: 128MB
   - タイムアウト: 10秒
   - **重要**: API GatewayからCognito User IDを取得し、S3パスに含める
   - 生成URL例: `s3://raw-bucket/raw/user-abc123/{filename}.json`

**Cognito User ID取得方法**:
```python
# API Gatewayのイベントから取得
def get_user_id(event):
    # API Gateway Cognito Authorizerから取得
    claims = event['requestContext']['authorizer']['claims']
    user_id = claims['sub']  # Cognito User ID (UUID)
    return user_id
```

#### 2.5 Cognito ユーザープール (`cdk/stacks/cognito_stack.py`) ✅

**新規追加**: AWS Cognito による認証

ユーザープール設定:
- サインイン: Email
- パスワードポリシー: 最小8文字、大小英字・数字必須
- MFA: オプション（無効でOK、個人利用のため）
- パスワードリセット: Email経由
- アカウント作成: 管理者のみ（セルフサインアップ無効）

作成するユーザー:
1. **自分用アカウント**: 管理者権限
2. **共有サンプルアカウント**: 閲覧専用（demo@example.com / DemoUser123!など）

Amplify連携:
- ユーザープールID、クライアントIDをAmplify環境変数に設定

#### 2.6 API Gateway (`cdk/stacks/api_stack.py`) ✅

REST API:
- `/upload-url` (GET) → upload-presigned Lambda
- `/chat` (POST) → chat-api Lambda
- CORS: Amplifyドメインのみ許可（本番）

**認証**: Cognito User Pool Authorizer
- 全エンドポイントでCognitoトークン検証必須
- 未認証リクエストは401エラー

#### 2.7 Amplify Hosting (`cdk/stacks/amplify_stack.py`) ✅

- GitHub連携
- 自動ビルド・デプロイ
- 環境変数:
  - `NEXT_PUBLIC_API_URL`: API GatewayのURL
  - `NEXT_PUBLIC_COGNITO_USER_POOL_ID`: CognitoユーザープールID
  - `NEXT_PUBLIC_COGNITO_CLIENT_ID`: CognitoクライアントID
  - `NEXT_PUBLIC_AWS_REGION`: AWSリージョン

### Phase 3: データ処理パイプライン実装 🔥 優先

#### 3.1 Glueジョブ (`glue_jobs/process_youtube_history.py`) ✅

**処理フロー**（**user_id対応**）:
1. 引数からINPUT_PATH、OUTPUT_PATH、user_idを取得
2. S3からJSONファイル読み込み（`s3://bucket/raw/{user_id}/{filename}.json`）
3. **広告レコードを除外**:
   - `details` に `"Google 広告から"` が含まれるレコードをフィルタ
4. YouTubeデータパース:
   - `video_title`: タイトルから「〇〇 を視聴しました」の部分を抽出
   - `video_id`: titleUrlから11文字の動画IDを抽出
   - `channel_name`: subtitles[0].nameから取得
   - `channel_id`: subtitles[0].urlからチャンネルIDを抽出
   - `watched_at`: timeをタイムスタンプに変換
5. Pandas DataFrameに変換
6. **user_idパーティションのみで**Parquet形式で保存（Snappy圧縮）
7. 出力先: `s3://bucket/processed/{user_id}/data.parquet`
   - **注意**: 日付パーティションなし（シンプル化）

**YouTube履歴JSONスキーマ**（Google Takeout形式）:
```json
[
  {
    "header": "YouTube",
    "title": "鈴木誠也「メジャー移籍から4年間のホームラン数は大谷に次ぐ日本人2位です」←これwww【ネット反応集】 を視聴しました",
    "titleUrl": "https://www.youtube.com/watch?v=HoASJiuVNhk",
    "subtitles": [{
      "name": "野球馬鹿チャンネル【ネット反応集】",
      "url": "https://www.youtube.com/channel/UCGtCj48DUKCTbaZdqOIpaJA"
    }],
    "time": "2025-12-27T10:26:59.596Z",
    "products": ["YouTube"],
    "activityControls": ["YouTube の再生履歴"]
  },
  {
    "header": "YouTube",
    "title": "YouTube のトップページで広告を視聴しました",
    "time": "2025-12-27T10:28:25.686Z",
    "products": ["YouTube"],
    "details": [{
      "name": "Google 広告から"
    }],
    "activityControls": ["ウェブとアプリのアクティビティ", "YouTube の再生履歴"]
  }
]
```

**広告の判定基準**:
- `details` 配列に `{"name": "Google 広告から"}` が含まれる場合は広告と判定し、除外する

**依存ライブラリ**:
- pandas, pyarrow (Glueジョブの `--additional-python-modules` パラメータで指定)
- boto3 (Glue Python Shell に標準で含まれる)

#### 3.2 Lambda trigger-glue (`lambdas/trigger_glue/handler.py`) ✅

```python
import boto3
import os

glue = boto3.client('glue')

def lambda_handler(event, context):
    # S3イベントからバケット名とキー取得
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # .jsonファイルのみ処理
        if not key.endswith('.json'):
            continue

        # S3パスからuser_idを抽出
        # 例: "raw/user-abc123/watch-history.json" -> "user-abc123"
        path_parts = key.split('/')
        if len(path_parts) < 2 or path_parts[0] != 'raw':
            print(f"Invalid path structure: {key}")
            continue

        user_id = path_parts[1]

        # Glueジョブ起動
        response = glue.start_job_run(
            JobName=os.environ['GLUE_JOB_NAME'],
            Arguments={
                '--INPUT_PATH': f's3://{bucket}/{key}',
                '--OUTPUT_PATH': os.environ['OUTPUT_BUCKET'],
                '--user_id': user_id  # ユーザーIDを渡す
            }
        )

        print(f"Started Glue job for user {user_id}: {response['JobRunId']}")

    return {'statusCode': 200}
```

### Phase 4: Lambda関数実装

#### 4.1 Athenaクライアント (`lambdas/shared/athena_client.py`) 🔄 後回し

機能:
- クエリ実行・結果取得
- **クエリキャッシング**（メモリ内、Lambda暖機時に有効）
- タイムアウト処理
- エラーハンドリング

#### 4.2 Bedrockクライアント (`lambdas/shared/bedrock_client.py`) 🔄 後回し

- モデル: Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`)
- リージョン: us-east-1（Bedrockが利用可能なリージョン）
- max_tokens: 2000（コスト最適化）
- temperature: 0.7

#### 4.3 チャットAPI Lambda (`lambdas/chat_api/handler.py`) 🔄 後回し

**処理フロー** (シンプルなキーワードマッチ方式 + **user_id フィルタリング**):

1. API GatewayからCognito User IDを取得
2. ユーザーの質問を受け取る
3. **キーワードマッチング**で適切なAthenaクエリを選択（**全てuser_idでフィルタ**）:
   - "most watched" → チャンネル別視聴回数TOP10（そのユーザーのみ）
   - "total videos" → 総視聴動画数（そのユーザーのみ）
   - "recent" / "最近" → 直近30日の視聴履歴（そのユーザーのみ）
   - デフォルト → 全データから100件サンプリング（そのユーザーのみ）
4. Athenaクエリ実行（キャッシング活用）
5. Bedrockに質問とデータを渡してプロンプト生成:
   ```
   以下のYouTube閲覧履歴データに基づいて質問に答えてください。

   データ: [Athenaクエリ結果]
   質問: [ユーザーの質問]

   データに基づいた具体的な回答を提供してください。
   ```
6. Bedrock回答を返す

**クエリ例** (user_idフィルタリング):
```python
def get_query(question, user_id):
    if 'most watched' in question.lower():
        return f"""
        SELECT channel_name, COUNT(*) as watch_count
        FROM youtube_watch_history
        WHERE user_id = '{user_id}'
        GROUP BY channel_name
        ORDER BY watch_count DESC
        LIMIT 10
        """
    elif 'total' in question.lower():
        return f"""
        SELECT COUNT(*) as total
        FROM youtube_watch_history
        WHERE user_id = '{user_id}'
        """
    else:
        return f"""
        SELECT title, channel_name, watched_at
        FROM youtube_watch_history
        WHERE user_id = '{user_id}'
        ORDER BY watched_at DESC
        LIMIT 100
        """
```

#### 4.4 Upload Presigned Lambda (`lambdas/upload_presigned/handler.py`) ✅

### Phase 5: フロントエンド実装 ✅

#### 5.1 Next.jsプロジェクト初期化 (`frontend/`) ✅

```bash
npx create-next-app@latest . --typescript --tailwind --app
npm install axios @aws-amplify/auth aws-amplify
```

**依存パッケージ**:
- `axios`: API呼び出し
- `@aws-amplify/auth`: Cognito認証
- `aws-amplify`: Amplify設定

#### 5.2 Cognito認証設定 (`frontend/src/lib/auth.ts`) ✅

AWS Amplify設定:
```typescript
import { Amplify } from 'aws-amplify';
import { signIn, signOut, getCurrentUser, fetchAuthSession } from '@aws-amplify/auth';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
      region: process.env.NEXT_PUBLIC_AWS_REGION!,
    }
  }
});

export { signIn, signOut, getCurrentUser, fetchAuthSession };
```

認証ヘルパー関数:
- `login(email, password)`: ログイン処理
- `logout()`: ログアウト処理
- `getIdToken()`: API呼び出し用のIDトークン取得
- `isAuthenticated()`: 認証状態チェック

#### 5.3 ログインフォーム (`frontend/src/components/LoginForm.tsx`) ✅

機能:
- Email/パスワード入力
- ログインボタン
- エラーメッセージ表示
- ログイン成功後、ホーム画面へリダイレクト

```typescript
'use client';
import { useState } from 'react';
import { signIn } from '@/lib/auth';
import { useRouter } from 'next/navigation';

export default function LoginForm() {
  // Email, パスワード入力
  // signIn()でCognito認証
  // 成功したら '/' へリダイレクト
}
```

#### 5.4 認証ガード (`frontend/src/components/AuthGuard.tsx`) ✅

機能:
- ページアクセス時に認証状態をチェック
- 未認証の場合、ログイン画面へリダイレクト
- 認証済みの場合、子コンポーネントを表示

```typescript
'use client';
import { useEffect, useState } from 'react';
import { getCurrentUser } from '@/lib/auth';
import { useRouter } from 'next/navigation';

export default function AuthGuard({ children }) {
  // getCurrentUser()で認証チェック
  // 未認証なら '/login' へリダイレクト
}
```

ホーム画面とチャット画面を `<AuthGuard>` でラップ

#### 5.5 ファイルアップロード (`frontend/src/components/FileUpload.tsx`) ✅

機能:
- JSONファイル選択
- `/upload-url` APIで署名付きURL取得（**認証トークンをヘッダーに付与**）
- S3へ直接アップロード（Lambdaを経由しない = コスト削減）
- アップロード状態表示

API呼び出し時の認証:
```typescript
const token = await getIdToken();
const { data } = await axios.get(
  `${API_URL}/upload-url?fileName=${file.name}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
```

#### 5.6 チャットインターフェース (`frontend/src/components/ChatInterface.tsx`) 🔄 後回し

機能:
- メッセージ履歴表示
- ユーザー入力
- `/chat` APIへPOSTリクエスト
- ストリーミングレスポンス対応（オプション）
- 質問例の表示:
  - 「最も視聴したチャンネルトップ10は？」
  - 「2024年に何本の動画を見ましたか？」
  - 「最近1ヶ月の視聴傾向は？」

API呼び出し時も同様に認証トークンをヘッダーに付与

#### 5.7 ページ構成 ✅

- `/login` (page.tsx): ログイン画面 - Cognito認証
- `/` (page.tsx): ホーム画面 - ファイルアップロード（認証必須）
- `/chat` (page.tsx): チャット画面 - データ分析（認証必須）🔄 後回し

### Phase 6: デプロイ・テスト 🔥 優先

#### 6.1 CDKデプロイ 🔥

```bash
cd cdk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap  # 初回のみ
cdk deploy --all
```

出力される値:
- API GatewayのURL
- S3バケット名
- Amplify App URL

#### 6.2 Cognitoユーザー作成 🔥

CDKデプロイ後、AWS CLIまたはコンソールでユーザー作成:

```bash
# 自分用アカウント作成
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username your-email@example.com \
  --user-attributes Name=email,Value=your-email@example.com \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS

# 共有サンプルアカウント作成
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username demo@example.com \
  --user-attributes Name=email,Value=demo@example.com \
  --temporary-password DemoUser123! \
  --message-action SUPPRESS

# 初回ログイン時にパスワード変更が必要
```

または、CDKスタック内でカスタムリソース（Lambda）を使用して自動作成も可能

#### 6.3 フロントエンド設定 🔥

1. GitHubリポジトリにコードpush
2. Amplify環境変数設定:
   - `NEXT_PUBLIC_API_URL`: API GatewayのURL
   - `NEXT_PUBLIC_COGNITO_USER_POOL_ID`: CognitoユーザープールID
   - `NEXT_PUBLIC_COGNITO_CLIENT_ID`: CognitoクライアントID
   - `NEXT_PUBLIC_AWS_REGION`: us-east-1（またはデプロイリージョン）
3. 自動ビルド・デプロイ開始

#### 6.4 初期テスト 🔥

**優先テスト（データパイプライン）**:
1. **ログインテスト**: demo@example.com でログイン確認
2. サンプルYouTube履歴JSON作成（Google Takeoutから取得）
3. フロントエンドからアップロード（認証済み状態で）
   - 確認: S3パスに正しくuser_idが含まれているか
4. CloudWatch Logsでジョブ実行確認
5. Athenaコンソールでデータ確認
   - 確認: user_idパーティションが正しく作成されているか
6. **別ユーザーでログイン**して、データ分離を確認
   - 確認: 他ユーザーのデータが見えないこと
7. ログアウト機能のテスト

**後回し（チャット機能テスト）**:
- チャット画面で質問テスト（認証済み状態で）
  - 確認: 自分のデータのみが返ってくるか

## ユーザーごとのデータ分離まとめ

### データフロー全体（ユーザー分離版）

```
1. ログイン
   ↓
   Cognito認証 → User ID (sub) 取得

2. アップロード
   ↓
   Lambda (upload-presigned) が User ID を含むS3パスで署名付きURL生成
   s3://raw-bucket/raw/{user-id}/watch-history.json

3. データ処理
   ↓
   S3イベント → Lambda (trigger-glue) がパスから user_id 抽出
   ↓
   Glue ジョブが user_id をパーティションに含めて Parquet 保存
   s3://processed-bucket/processed/{user-id}/year=2025/month=01/day=15/

4. クエリ
   ↓
   Lambda (chat-api) が Cognito から user_id 取得
   ↓
   Athena クエリに WHERE user_id = '{user_id}' を追加
   ↓
   自分のデータのみ取得
```

### セキュリティ保証

1. **アップロード時**: Lambda関数がCognito User IDを使用してS3パスを生成
   - 他ユーザーのパスには書き込めない

2. **クエリ時**: Lambda関数がCognito User IDでAthenaクエリをフィルタ
   - 他ユーザーのデータは取得できない

3. **S3アクセス**: バケットポリシーでパブリックアクセスブロック
   - 直接S3アクセスは不可

4. **期間限定**: 2日後に全データ自動削除
   - 検証用途に最適

## コスト最適化ポイント

| 項目 | 最適化手法 | 効果 |
|------|-----------|------|
| データウェアハウス | ❌ Redshift → ✅ Athena | 月$50-100 → $0.05/10GB |
| データ処理 | ❌ Glue ETL (2+ DPU) → ✅ Glue Python Shell (1 DPU) | 大幅削減 |
| BI可視化 | ❌ QuickSight → ✅ チャットUI | $9/月 → $0 |
| セキュリティ | ❌ AWS WAF → ✅ APIキー | $5/月 → $0 |
| 定期実行 | ❌ EventBridge → ✅ 手動アップロード | 不要 |
| Athenaクエリ | クエリ結果キャッシング | 再スキャン削減 |
| S3ストレージ | ライフサイクルポリシー | 古いデータ削除 |
| Lambda | 適切なメモリ設定 | 実行コスト削減 |

**月額コスト見積もり**（個人利用・月100リクエスト想定）:
- S3: $0.02
- Lambda: $0.00（無料枠内）
- Glue Python Shell: $0.22
- Athena: $0.05
- Bedrock: $3.00（主要コスト）
- Cognito: $0.00（50,000 MAU まで無料）
- Amplify: $0.15
- **合計: 約$3.50/月**

## セキュリティ考慮事項

1. **Cognito認証**: 全APIエンドポイントでJWTトークン検証必須
2. **ユーザーごとのデータ分離**:
   - S3パスにCognito User IDを使用
   - Lambda関数でUser IDを検証してS3パス生成
   - AthenaクエリでUser IDフィルタリング必須
   - 他ユーザーのデータへのアクセスを完全にブロック
3. **IAM最小権限の原則**: 各Lambda関数に必要最小限の権限のみ付与
4. **S3バケットポリシー**: パブリックアクセスブロック有効
5. **パスワードポリシー**: 最小8文字、大小英字・数字必須
6. **環境変数**: シークレット情報は環境変数で管理（.envファイルは.gitignore）
7. **CORS設定**: Amplifyドメインのみ許可
8. **セルフサインアップ無効**: 管理者のみがユーザー作成可能
9. **期間限定保存**: 2日後に自動削除でデータ漏洩リスク最小化（検証用）

## モニタリング・ログ

- **CloudWatch Logs**: 全Lambda関数、Glueジョブのログ自動出力
- **CloudWatch Metrics**: Lambda実行回数、エラー率、実行時間
- **Athenaクエリ履歴**: クエリパフォーマンスの確認
- **コストエクスプローラー**: 月次コスト監視

## 今後の拡張案

1. **データビジュアライゼーション**: Chart.jsで視聴傾向グラフ表示
2. **高度なクエリ生成**: BedrockのFunction Calling機能でAthenaクエリを動的生成
3. **他のTakeoutデータ対応**: 検索履歴、位置情報など
4. **レコメンデーション**: 視聴傾向から新チャンネル推薦
5. **ユーザーごとのデータ分離**: S3パスにユーザーIDを含めて複数ユーザー対応
6. **ストリーミングレスポンス**: Bedrock回答のリアルタイム表示

## 重要な実装ファイル（優先順）

1. **`cdk/app.py`** - CDKエントリーポイント、全スタック統合
2. **`cdk/stacks/storage_stack.py`** - S3バケット定義
3. **`cdk/stacks/cognito_stack.py`** - Cognitoユーザープール（**新規追加**）
4. **`cdk/stacks/glue_stack.py`** - Glueジョブ定義
5. **`cdk/stacks/lambda_stack.py`** - Lambda関数デプロイ
6. **`cdk/stacks/api_stack.py`** - API Gateway + Cognito Authorizer（**更新**）
7. **`glue_jobs/process_youtube_history.py`** - データ加工コアロジック
8. **`lambdas/chat_api/handler.py`** - チャットAPI、Athena + Bedrock統合
9. **`lambdas/shared/athena_client.py`** - Athenaクライアント + キャッシング
10. **`lambdas/shared/bedrock_client.py`** - Bedrockクライアント
11. **`frontend/src/lib/auth.ts`** - Cognito認証ヘルパー（**新規追加**）
12. **`frontend/src/components/LoginForm.tsx`** - ログインUI（**新規追加**）
13. **`frontend/src/components/AuthGuard.tsx`** - 認証ガード（**新規追加**）
14. **`frontend/src/components/ChatInterface.tsx`** - チャットUI
15. **`frontend/src/components/FileUpload.tsx`** - アップロードUI

## 参考資料

- [AWS Glue Python Shell (コスト効率)](https://cloudchipr.com/blog/aws-glue-pricing)
- [AWS Athena Partition Projection](https://aws.amazon.com/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena/)
- [YouTube Takeout JSON構造](https://portmap.dtinit.org/articles/watch-history2.md/)
- [AWS Bedrock Claude統合](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html)
- [AWS CDK Python Examples](https://github.com/aws-samples/aws-cdk-examples/tree/master/python)
