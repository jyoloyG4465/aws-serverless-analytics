"""
YouTube閲覧履歴JSONをParquet形式に変換するGlue Python Shellジョブ

実際のYouTube履歴JSON形式（Google Takeout）:
[{
  "header": "YouTube",
  "title": "〇〇 を視聴しました",
  "titleUrl": "https://www.youtube.com/watch?v=VIDEO_ID",
  "subtitles": [{
    "name": "チャンネル名",
    "url": "https://www.youtube.com/channel/CHANNEL_ID"
  }],
  "time": "2025-12-27T10:26:59.596Z",
  "products": ["YouTube"],
  "activityControls": ["YouTube の再生履歴"]
},{
  "header": "YouTube",
  "title": "YouTube のトップページで広告を視聴しました",
  "time": "2025-12-27T10:28:25.686Z",
  "products": ["YouTube"],
  "details": [{"name": "Google 広告から"}],
  "activityControls": ["ウェブとアプリのアクティビティ", "YouTube の再生履歴"]
}]
"""

import sys
import json
import re
from datetime import datetime
import boto3
import pandas as pd
from awsglue.utils import getResolvedOptions


def is_advertisement(record: dict) -> bool:
    """
    広告かどうかを判定

    判定基準:
    - details 配列に {"name": "Google 広告から"} が含まれる
    """
    details = record.get('details', [])
    for detail in details:
        if isinstance(detail, dict) and detail.get('name') == 'Google 広告から':
            return True
    return False


def extract_video_title(title: str) -> str:
    """
    動画タイトルを抽出

    「〇〇 を視聴しました」から動画タイトル部分を抽出
    """
    if not title:
        return ""

    # 「〇〇 を視聴しました」パターン
    match = re.search(r'(.+?)\s*を視聴しました', title)
    if match:
        return match.group(1).strip()

    # パターンにマッチしない場合はそのまま返す
    return title


def extract_video_id(url: str) -> str:
    """
    URLから動画ID（11文字）を抽出

    対応パターン:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    if not url:
        return ""

    # watch?v=VIDEO_ID パターン
    match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)

    # youtu.be/VIDEO_ID パターン
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)

    return ""


def extract_channel_id(url: str) -> str:
    """
    URLからチャンネルIDを抽出

    対応パターン:
    - https://www.youtube.com/channel/CHANNEL_ID
    """
    if not url:
        return ""

    # /channel/CHANNEL_ID パターン
    match = re.search(r'/channel/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    return ""


def process_youtube_history(
    input_path: str,
    output_path: str,
    user_id: str
) -> None:
    """
    YouTube履歴JSONをParquet形式に変換

    Args:
        input_path: S3上の入力JSONパス（s3://bucket/key形式）
        output_path: S3上の出力バケット名
        user_id: ユーザーID
    """
    s3 = boto3.client('s3')

    # S3パスをパース
    input_parts = input_path.replace('s3://', '').split('/', 1)
    input_bucket = input_parts[0]
    input_key = input_parts[1]

    print(f"Reading from s3://{input_bucket}/{input_key}")

    # S3からJSONを読み込み
    try:
        response = s3.get_object(Bucket=input_bucket, Key=input_key)
        json_content = response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error reading from S3: {str(e)}")
        raise

    # JSONをパース
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
        raise

    if not isinstance(data, list):
        raise ValueError("JSON must be an array of records")

    print(f"Loaded {len(data)} records")

    # データを変換
    records = []
    ad_count = 0

    for item in data:
        # 広告を除外
        if is_advertisement(item):
            ad_count += 1
            continue

        # 基本情報を抽出
        title = item.get('title', '')
        title_url = item.get('titleUrl', '')
        time_str = item.get('time', '')
        subtitles = item.get('subtitles', [])

        # タイムスタンプをパース
        try:
            watched_at = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except Exception as e:
            print(f"Failed to parse time: {time_str}, error: {e}")
            continue

        # 動画情報を抽出
        video_title = extract_video_title(title)
        video_id = extract_video_id(title_url)

        # チャンネル情報を抽出
        channel_name = ""
        channel_id = ""
        if subtitles and len(subtitles) > 0:
            first_subtitle = subtitles[0]
            if isinstance(first_subtitle, dict):
                channel_name = first_subtitle.get('name', '')
                channel_url = first_subtitle.get('url', '')
                channel_id = extract_channel_id(channel_url)

        # レコードを作成
        record = {
            'title': video_title,
            'video_id': video_id,
            'channel_name': channel_name,
            'channel_id': channel_id,
            'watched_at': watched_at,
        }

        records.append(record)

    print(f"Processed {len(records)} valid records (excluded {ad_count} advertisements)")

    if not records:
        print("No valid records to process")
        return

    # DataFrameに変換
    df = pd.DataFrame(records)

    # watched_atはdatetime型のまま保存（Parquetはtimestamp型をネイティブサポート）

    # 出力パスを生成（user_idパーティションのみ）
    # 例: s3://jyoloyg-processed/processed/user-abc123/data.parquet
    output_s3_path = f"s3://{output_path}/processed/{user_id}/data.parquet"

    print(f"Writing to {output_s3_path}")
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")

    # Parquet形式で保存（Snappy圧縮）
    try:
        df.to_parquet(
            output_s3_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
    except Exception as e:
        print(f"Error writing Parquet to S3: {str(e)}")
        raise

    print(f"Successfully wrote {len(df)} records to {output_s3_path}")

    # 統計情報を出力
    print("\n=== Statistics ===")
    print(f"Total input records: {len(data)}")
    print(f"Advertisements excluded: {ad_count}")
    print(f"Valid video records: {len(df)}")
    if len(df) > 0:
        print(f"Date range: {df['watched_at'].min()} to {df['watched_at'].max()}")
        print(f"Unique channels: {df['channel_name'].nunique()}")
        print(f"Top 5 channels:")
        top_channels = df['channel_name'].value_counts().head(5)
        for channel, count in top_channels.items():
            print(f"  - {channel}: {count} videos")


def main():
    """
    メイン処理

    Glueジョブの引数:
    - INPUT_PATH: S3上の入力JSONパス
    - OUTPUT_PATH: S3上の出力バケット名
    - user_id: ユーザーID
    """
    # Glueジョブの引数を取得
    args = getResolvedOptions(sys.argv, ['INPUT_PATH', 'OUTPUT_PATH', 'user_id'])

    input_path = args['INPUT_PATH']
    output_path = args['OUTPUT_PATH']
    user_id = args['user_id']

    print(f"Starting YouTube history processing")
    print(f"Input: {input_path}")
    print(f"Output bucket: {output_path}")
    print(f"User ID: {user_id}")

    try:
        process_youtube_history(input_path, output_path, user_id)
        print("\n✅ Job completed successfully")
    except Exception as e:
        print(f"\n❌ Job failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
