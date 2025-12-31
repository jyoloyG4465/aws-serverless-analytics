"""
S3署名付きURL生成Lambda関数

API Gatewayから呼び出され、Cognito User IDを基にS3署名付きURLを生成
パス: s3://jyoloyg-raw/raw/{user_id}/{filename}
"""

import os
import json
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')


def get_user_id_from_event(event):
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
        # Cognito Authorizerから認証情報を取得
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        claims = authorizer.get('claims', {})
        user_id = claims.get('sub')

        if not user_id:
            raise ValueError("User ID (sub) not found in Cognito claims")

        return user_id

    except Exception as e:
        print(f"Error extracting user_id: {str(e)}")
        raise ValueError(f"Failed to get user ID from request: {str(e)}")


def lambda_handler(event, context):
    """
    Lambda handler

    リクエストボディ (JSON):
        fileName: アップロードするファイル名

    レスポンス:
        {
            "uploadUrl": "署名付きURL",
            "key": "S3オブジェクトキー",
            "expiresIn": 有効期限（秒）
        }
    """
    print(f"Received event: {json.dumps(event)}")

    # CORS対応のレスポンスヘッダー
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    }

    try:
        # 環境変数を取得
        raw_bucket = os.environ.get('RAW_BUCKET')
        if not raw_bucket:
            raise ValueError("RAW_BUCKET environment variable not set")

        # Cognito User IDを取得
        user_id = get_user_id_from_event(event)
        print(f"User ID: {user_id}")

        # リクエストボディからファイル名を取得
        body = event.get('body')
        if not body:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Request body is required'
                })
            }

        # ボディがJSON文字列の場合はパース
        if isinstance(body, str):
            body = json.loads(body)

        file_name = body.get('fileName')

        if not file_name:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'fileName is required in request body'
                })
            }

        # ファイル名のバリデーション（基本的なチェック）
        if not file_name.endswith('.json'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Only .json files are supported'
                })
            }

        # S3オブジェクトキーを生成
        # パス: raw/{user_id}/{filename}
        object_key = f"raw/{user_id}/{file_name}"
        print(f"S3 object key: {object_key}")

        # 署名付きURL生成（PUT用、有効期限5分）
        expires_in = 300  # 5分

        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': raw_bucket,
                'Key': object_key,
                'ContentType': 'application/json',
            },
            ExpiresIn=expires_in,
            HttpMethod='PUT'
        )

        print(f"✅ Generated presigned URL for s3://{raw_bucket}/{object_key}")

        # レスポンス
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'key': object_key,
                'bucket': raw_bucket,
                'expiresIn': expires_in,
                'message': f'Upload your file to the provided URL within {expires_in} seconds'
            })
        }

    except ValueError as e:
        # バリデーションエラー
        print(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': str(e)
            })
        }

    except ClientError as e:
        # AWS APIエラー
        print(f"AWS error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Failed to generate presigned URL',
                'details': str(e)
            })
        }

    except Exception as e:
        # その他のエラー
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
