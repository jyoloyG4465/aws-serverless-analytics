# YouTube閲覧履歴分析 - AWS サーバーレスアプリケーション

YouTube閲覧履歴（Google Takeout JSON）をAWSで分析し、Amazon Bedrockを使ったAIチャットインターフェースで質問できるサーバーレスアプリケーションです。

## 主要機能

- **認証システム**: AWS Cognito による安全なユーザー認証
- **ユーザーごとのデータ完全分離**: S3パスとCognito User IDでデータを分離
- **自動データ処理**: JSONアップロード → Glue Python Shellで自動加工 → Parquet形式で保存
- **高速クエリ**: Amazon Athenaによるサーバーレスデータ分析
- **ハイブリッド検索**: キーワード検出でAthena（SQLクエリ）とRAG（ベクトル検索）を自動選択
- **ベクトル検索**: Amazon Titan Embeddingsによるセマンティック検索（RAG）
- **AIチャット**: Amazon Bedrock (Claude 3.5 Sonnet) による自然言語での質問応答
- **ストリーミング表示**: チャット応答のリアルタイムストリーミング
- **データステータス確認**: チャット画面表示前に自動でデータ存在を確認
- **デモデータ**: テスト用サンプルデータのダウンロード機能
- **期間限定保存**: 30日後に自動削除（デモ・検証用途）

## システムアーキテクチャ

```
ユーザー → Next.js (Amplify)
             ↓ アップロード
          S3 (raw-data)
             ↓ EventBridge
          Lambda (trigger_glue) → Glue Python Shell
                                   ↓ Parquet変換
                                S3 (processed-data)
                                   ↓ EventBridge
                                Lambda (vectorize)
                                   ↓ Titan Embeddings
                                S3 (vectors)

チャット質問 → API Gateway → Lambda (chat_api)
                              ↓ 質問タイプ判定
                        ┌─────┴─────┐
                     Athena       RAG検索
                     (SQL)     (ベクトル検索)
                        └─────┬─────┘
                           Bedrock (Claude)
                              ↓
                           AI回答（ストリーミング）
```

## データ処理フロー

1. **アップロード**: JSONファイルをS3 raw/ にアップロード
2. **変換**: EventBridgeがGlueジョブをトリガー → Parquet形式に変換
3. **ベクトル化**: EventBridgeがvectorize Lambdaをトリガー → Titan Embeddingsでベクトル化
4. **検索**: チャット時にハイブリッド検索（Athena or RAG）で適切な方式を自動選択

### ハイブリッド検索の仕組み

- **Athenaクエリ**: 「トップ10」「集計」「ランキング」などの数値・集計系質問
- **RAG検索**: 「○○について」「どんな動画」などの意味検索・文脈理解が必要な質問

## 技術スタック

### フロントエンド
- Next.js 14 (App Router)
- React + TypeScript
- Tailwind CSS
- AWS Amplify (Hosting + Cognito認証)

### バックエンド
- **データ処理**: AWS Glue Python Shell
- **クエリエンジン**: Amazon Athena
- **AI分析**: Amazon Bedrock
  - Claude 3.5 Sonnet（チャット応答）
  - Titan Embeddings（ベクトル化・RAG検索）
- **API**: AWS Lambda + API Gateway
- **認証**: Amazon Cognito
- **ストレージ**: Amazon S3
- **イベント連携**: Amazon EventBridge

### インフラストラクチャ
- AWS CDK (Python)

## プロジェクト構造

```
aws-serverless-analytics/
├── cdk/                    # AWS CDK インフラ定義
│   ├── app.py
│   ├── requirements.txt
│   └── stacks/
├── lambdas/                # Lambda関数
│   ├── shared/             # 共通ライブラリ（Lambda Layer）
│   ├── trigger_glue/       # Glueジョブトリガー
│   ├── chat_api/           # チャットAPI（ハイブリッド検索）
│   ├── upload_presigned/   # S3署名付きURL生成
│   ├── vectorize/          # ベクトル化（RAG用）
│   └── check_data_status/  # データ存在確認
├── glue_jobs/              # Glueデータ処理スクリプト
├── front-end/              # Next.jsフロントエンド
└── docs/                   # ドキュメント
```

## セットアップ

### 前提条件

- Node.js 18+
- Python 3.9+
- AWS CLI設定済み
- AWS CDK CLI (`npm install -g aws-cdk`)

### 1. 環境変数設定

```bash
cp .env.example .env
# .envファイルを編集してAWSアカウント情報を設定
```

### 2. CDKインフラデプロイ

```bash
cd cdk
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 初回のみ
cdk bootstrap

# デプロイ
cdk deploy --all
```

### 3. Cognitoユーザー作成

```bash
# 出力されたユーザープールIDを使用
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username your-email@example.com \
  --user-attributes Name=email,Value=your-email@example.com \
  --temporary-password TempPassword123!
```

### 4. フロントエンド設定

```bash
cd front-end
npm install

# 環境変数を設定（AmplifyまたはVercel）
# NEXT_PUBLIC_API_URL, NEXT_PUBLIC_COGNITO_USER_POOL_ID など

npm run dev  # ローカル開発サーバー
```

## 使い方

1. **ログイン**: Cognitoアカウントでログイン
2. **データアップロード**: Google TakeoutのYouTube履歴JSONをアップロード
   - テスト用にはデモデータダウンロード機能を利用可能
3. **データ処理待機**: 数分でGlueジョブがParquet形式に自動変換し、ベクトル化も実行
4. **チャットで質問**:

### 質問例

#### 集計・ランキング系（Athenaで処理）
- 「最も視聴したチャンネルトップ10は？」
- 「2024年に何本の動画を見ましたか？」
- 「月別の視聴本数を教えて」

#### 意味検索系（RAGで処理）
- 「プログラミング学習に関する動画は？」
- 「料理レシピ系で印象に残った動画を教えて」
- 「最近の視聴傾向を分析して」

## データ管理ポリシー

### ユーザーごとのデータ分離
- S3パス: `s3://bucket/{cognito-user-id}/`
- 各ユーザーは自分のデータのみアクセス可能
- Athenaクエリで自動的に`user_id`フィルタ適用

### 自動削除
- アップロードから30日後に全データ自動削除（S3ライフサイクルポリシー）
- Athenaクエリ結果は7日後に削除

## コスト見積もり

個人利用・月100リクエスト想定で **約$3.50/月**:

| サービス | 月額コスト |
|---------|----------|
| S3 | $0.02 |
| Lambda | $0.00（無料枠内） |
| Glue Python Shell | $0.22 |
| Athena | $0.05 |
| Bedrock (Claude 3.5) | $3.00 |
| Bedrock (Titan Embeddings) | $0.05 |
| Cognito | $0.00（無料枠内） |
| Amplify | $0.15 |

## セキュリティ

- ✅ Cognito JWT認証（全APIエンドポイント）
- ✅ ユーザーごとのS3パス分離
- ✅ IAM最小権限の原則
- ✅ S3パブリックアクセスブロック
- ✅ CORS設定（Amplifyドメインのみ許可）
- ✅ 30日自動削除でデータ漏洩リスク最小化

## 開発者向け

### ローカルテスト

```bash
# Glueジョブのローカルテスト
cd glue_jobs
python test_local.py

# Lambda関数のテスト
cd lambdas/chat_api
python -m pytest
```

### デプロイメント

```bash
# CDKスタック更新
cd cdk
cdk diff
cdk deploy --all

# フロントエンド（Amplifyが自動デプロイ）
git push origin main
```

## トラブルシューティング

- **Glueジョブが失敗**: CloudWatch Logsで詳細確認
- **Athenaクエリが遅い**: Partition Projection設定確認
- **Bedrock 403エラー**: us-east-1リージョンでモデルアクセス有効化
- **ベクトル化が完了しない**: vectorize Lambdaのログを確認
- **チャット画面が表示されない**: データステータスAPIでデータ存在を確認

## ライセンス

MIT License

## 参考資料

- [AWS Glue Python Shell](https://docs.aws.amazon.com/glue/latest/dg/add-job-python.html)
- [Amazon Athena](https://docs.aws.amazon.com/athena/)
- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Amazon Titan Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [AWS CDK Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
