"""
データステータスチェック Lambda 関数

S3にユーザーのベクトルデータが存在するかチェック
パス: s3://{VECTORS_BUCKET}/vectors/{user_id}/embeddings.json
"""

import json
import os

import boto3
from botocore.exceptions import ClientError
from shared.response import error, options, success

s3 = boto3.client("s3")


def get_user_id_from_event(event: dict) -> str:
    """
    API GatewayイベントからCognito User IDを取得

    Args:
        event: API Gatewayイベント

    Returns:
        str: Cognito User ID (sub)

    Raises:
        ValueError: User IDが取得できない場合
    """
    try:
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        user_id = claims.get("sub")

        if not user_id:
            raise ValueError("User ID (sub) not found in Cognito claims")

        return user_id

    except Exception as e:
        print(f"Error extracting user_id: {str(e)}")
        raise ValueError(f"Failed to get user ID from request: {str(e)}")


def check_vectors_exist(bucket: str, user_id: str) -> bool:
    """
    S3にベクトルデータが存在するかチェック

    Args:
        bucket: S3バケット名
        user_id: ユーザーID

    Returns:
        bool: 存在する場合True
    """
    key = f"vectors/{user_id}/embeddings.json"

    try:
        s3.head_object(Bucket=bucket, Key=key)
        print(f"Vectors found: s3://{bucket}/{key}")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            print(f"Vectors not found: s3://{bucket}/{key}")
            return False
        # 404以外のエラーは再raise
        print(f"S3 error: {str(e)}")
        raise


def lambda_handler(event: dict, context) -> dict:
    """
    Lambda handler

    レスポンス:
        {
            "hasData": true/false,
            "message": "ステータスメッセージ"
        }
    """
    print(f"Received event: {json.dumps(event)}")

    # CORS プリフライト
    if event.get("httpMethod") == "OPTIONS":
        return options()

    try:
        # 環境変数を取得
        vectors_bucket = os.environ.get("VECTORS_BUCKET")
        if not vectors_bucket:
            raise ValueError("VECTORS_BUCKET environment variable not set")

        # Cognito User IDを取得
        user_id = get_user_id_from_event(event)
        print(f"User ID: {user_id}")

        # ベクトルデータの存在チェック
        has_data = check_vectors_exist(vectors_bucket, user_id)

        if has_data:
            return success(
                {
                    "hasData": True,
                    "message": "データが見つかりました。チャットを開始できます。",
                }
            )
        else:
            return success(
                {
                    "hasData": False,
                    "message": "データが見つかりません。新しいデータをアップロード済みの場合は、数分後に反映されます。",
                }
            )

    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return error(str(e), 400)

    except ClientError as e:
        print(f"AWS error: {str(e)}")
        return error("Failed to check data status", 500, str(e))

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        return error("Internal server error", 500, str(e))
