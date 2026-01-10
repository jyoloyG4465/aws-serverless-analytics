"""
S3イベントトリガーでGlueジョブを起動するLambda関数

S3パス構造: s3://jyoloyg-raw/raw/{user_id}/{filename}.json
処理: JSONファイルがアップロードされたらGlueジョブを起動
"""

import os
import json
import boto3

from shared.response import success, error

glue = boto3.client('glue')


def lambda_handler(event, context):
    """
    S3イベントハンドラー
    EventBridge形式とS3イベント通知形式の両方に対応

    Args:
        event: S3イベントまたはEventBridgeイベント
        context: Lambda context

    Returns:
        dict: レスポンス
    """
    print(f"Received event: {json.dumps(event)}")

    # 環境変数を取得
    glue_job_name = os.environ.get('GLUE_JOB_NAME')
    output_bucket = os.environ.get('OUTPUT_BUCKET')

    if not glue_job_name or not output_bucket:
        return error(
            "Missing required environment variables: GLUE_JOB_NAME or OUTPUT_BUCKET",
            500
        )

    # S3イベントを処理
    processed_count = 0

    # EventBridge形式かS3イベント通知形式かを判定
    if 'detail' in event and event.get('source') == 'aws.s3':
        # EventBridge形式
        print("Processing EventBridge event")
        records = [{'s3': {'bucket': event['detail']['bucket'], 'object': event['detail']['object']}}]
    else:
        # S3イベント通知形式
        print("Processing S3 event notification")
        records = event.get('Records', [])

    for record in records:
        try:
            # S3イベント情報を取得
            s3_info = record.get('s3', {})
            bucket_name = s3_info.get('bucket', {}).get('name', '')
            object_key = s3_info.get('object', {}).get('key', '')

            print(f"Processing: s3://{bucket_name}/{object_key}")

            # .jsonファイルのみ処理
            if not object_key.endswith('.json'):
                print(f"Skipping non-JSON file: {object_key}")
                continue

            # S3パスからuser_idを抽出
            # 期待されるパス: raw/{user_id}/{filename}.json
            path_parts = object_key.split('/')

            if len(path_parts) < 3 or path_parts[0] != 'raw':
                print(f"Invalid path structure: {object_key}. Expected: raw/{{user_id}}/{{filename}}.json")
                continue

            user_id = path_parts[1]

            if not user_id:
                print(f"Empty user_id in path: {object_key}")
                continue

            print(f"Extracted user_id: {user_id}")

            # Glueジョブを起動
            input_path = f"s3://{bucket_name}/{object_key}"

            response = glue.start_job_run(
                JobName=glue_job_name,
                Arguments={
                    '--INPUT_PATH': input_path,
                    '--OUTPUT_PATH': output_bucket,
                    '--user_id': user_id,
                }
            )

            job_run_id = response.get('JobRunId')
            print(f"Started Glue job for user {user_id}: {job_run_id}")
            print(f"   Input: {input_path}")
            print(f"   Output: s3://{output_bucket}/processed/{user_id}/")

            processed_count += 1

        except Exception as e:
            print(f"Error processing record: {str(e)}")
            import traceback
            traceback.print_exc()
            # エラーがあっても他のレコードの処理を続行
            continue

    print(f"Processed {processed_count} file(s)")

    return success({
        'message': f'Successfully processed {processed_count} file(s)',
        'processed_count': processed_count
    })
