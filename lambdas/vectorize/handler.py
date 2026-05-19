"""
YouTube視聴履歴をベクトル化するLambda関数

処理フロー:
1. S3からParquetを読み込み
2. テキストをベクトル化（Bedrock Titan Embeddings）
3. S3にベクトルデータを保存
"""

import json
import os
import boto3
import pandas as pd
from io import BytesIO

from shared.response import success, error

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")

# Titan Embeddings モデル
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024

# ランダムサンプリング上限（Lambda メモリ・タイムアウト対策）
MAX_RECORDS = 4000


def parse_event(event: dict) -> list:
    """
    EventBridgeまたはS3通知イベントを統一形式に変換

    EventBridge形式:
      {"detail-type": "Object Created", "detail": {"bucket": {...}, "object": {...}}}

    S3通知形式:
      {"Records": [{"s3": {"bucket": {...}, "object": {...}}}]}
    """
    # EventBridge形式
    if "detail-type" in event and event.get("source") == "aws.s3":
        detail = event.get("detail", {})
        return [{
            "s3": {
                "bucket": detail.get("bucket", {}),
                "object": detail.get("object", {})
            }
        }]

    # S3通知形式
    return event.get("Records", [])


def lambda_handler(event, context):
    """
    S3イベントハンドラー（EventBridge経由）
    processed/{user_id}/data.parquet が作成されたらトリガー
    """
    print(f"Event: {json.dumps(event)}")

    vectors_bucket = os.environ.get("VECTORS_BUCKET")
    if not vectors_bucket:
        return error("VECTORS_BUCKET not set", 500)

    processed_count = 0

    # イベントソースに応じてレコードを抽出
    records = parse_event(event)

    for record in records:
        try:
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            print(f"Processing: s3://{bucket}/{key}")

            # processed/{user_id}/data.parquet のみ処理
            if not key.startswith("processed/") or not key.endswith(".parquet"):
                print(f"Skipping: {key}")
                continue

            # user_id を抽出
            parts = key.split("/")
            if len(parts) < 3:
                print(f"Invalid path: {key}")
                continue
            user_id = parts[1]

            # Parquet読み込み
            df = read_parquet_from_s3(bucket, key)
            print(f"Loaded {len(df)} records for user {user_id}")

            # ランダムサンプリング（5000件上限）
            if len(df) > MAX_RECORDS:
                print(f"Sampling {MAX_RECORDS} records from {len(df)}")
                df = df.sample(n=MAX_RECORDS, random_state=42)

            # ベクトル化
            vectors_data = vectorize_data(df, user_id)

            # S3に保存
            output_key = f"vectors/{user_id}/embeddings.json"
            save_vectors_to_s3(vectors_bucket, output_key, vectors_data)

            print(f"Saved vectors to s3://{vectors_bucket}/{output_key}")
            processed_count += 1

        except Exception as e:
            print(f"Error processing record: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    return success({
        "message": f"Processed {processed_count} file(s)",
        "processed_count": processed_count
    })


def read_parquet_from_s3(bucket: str, key: str) -> pd.DataFrame:
    """S3からParquetを読み込み"""
    response = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_parquet(BytesIO(response["Body"].read()))


def vectorize_data(df: pd.DataFrame, user_id: str) -> dict:
    """
    DataFrameをベクトル化

    各レコードを「タイトル - チャンネル名」のテキストに変換し、
    Bedrock Titan Embeddings でベクトル化
    """
    vectors = []
    texts = []
    metadata = []

    for idx, row in df.iterrows():
        # テキスト作成
        text = f"{row.get('title', '')} - {row.get('channel_name', '')}"
        texts.append(text)

        # メタデータ
        metadata.append({
            "title": row.get("title", ""),
            "channel_name": row.get("channel_name", ""),
            "video_id": row.get("video_id", ""),
            "watched_at": str(row.get("watched_at", ""))
        })

    # バッチでベクトル化（Titan Embeddings は1リクエスト1テキスト）
    print(f"Vectorizing {len(texts)} texts...")

    for i, text in enumerate(texts):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(texts)}")

        embedding = get_embedding(text)
        vectors.append(embedding)

    return {
        "user_id": user_id,
        "count": len(vectors),
        "dimension": EMBEDDING_DIMENSION,
        "vectors": vectors,
        "texts": texts,
        "metadata": metadata
    }


def get_embedding(text: str) -> list:
    """
    Bedrock Titan Embeddings でテキストをベクトル化
    """
    # テキストが空の場合はゼロベクトル
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMENSION

    # テキストを8000文字に制限（Titan制限）
    text = text[:8000]

    try:
        response = bedrock.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    except Exception as e:
        print(f"Embedding error for text '{text[:50]}...': {str(e)}")
        return [0.0] * EMBEDDING_DIMENSION


def save_vectors_to_s3(bucket: str, key: str, data: dict):
    """ベクトルデータをS3に保存"""
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False),
        ContentType="application/json"
    )
