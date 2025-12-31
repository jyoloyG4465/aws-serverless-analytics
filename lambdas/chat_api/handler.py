"""
Athena + Bedrock 統合チャット API Lambda 関数

機能:
- Cognito User ID によるデータ分離
- キーワードマッチングによる Athena クエリ選択
- Bedrock (Claude 3.5 Sonnet) による AI 分析
- CORS 対応
"""
import json
import os
from typing import Dict, Any

from shared.athena_client import AthenaClient, get_sample_queries
from shared.bedrock_client import BedrockClient


# 環境変数
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'youtube_analytics_db')
ATHENA_OUTPUT_LOCATION = os.environ.get('ATHENA_OUTPUT_LOCATION')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-northeast-1')

# CORS ヘッダー
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',  # 本番環境では Amplify ドメインに制限推奨
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler

    Args:
        event: API Gateway イベント
        context: Lambda コンテキスト

    Returns:
        API Gateway レスポンス
    """
    print(f"Event: {json.dumps(event)}")

    # OPTIONS リクエスト（CORS プリフライト）
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    try:
        # Cognito User ID を取得
        user_id = get_user_id(event)
        print(f"User ID: {user_id}")

        # リクエストボディをパース
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', '').strip()

        if not question:
            return error_response('Question is required', 400)

        print(f"Question: {question}")

        # Athena クライアント初期化
        athena_client = AthenaClient(
            database=ATHENA_DATABASE,
            output_location=ATHENA_OUTPUT_LOCATION,
            region=AWS_REGION
        )

        # クエリ選択（キーワードマッチング）
        query = select_query(question, user_id)
        print(f"Selected query type: {query[:100]}...")

        # Athena クエリ実行
        data = athena_client.execute_query(query, use_cache=True, timeout=25)
        print(f"Query returned {len(data)} rows")

        # Bedrock クライアント初期化
        bedrock_client = BedrockClient(
            region=AWS_REGION,
            max_tokens=2000,
            temperature=0.7
        )

        # AI 分析
        answer = bedrock_client.analyze_youtube_data(
            question=question,
            data=data
        )

        # 成功レスポンス
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'answer': answer,
                'data_count': len(data)
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Internal server error: {str(e)}", 500)


def get_user_id(event: Dict[str, Any]) -> str:
    """
    API Gateway イベントから Cognito User ID を取得

    Args:
        event: API Gateway イベント

    Returns:
        Cognito User ID (sub)

    Raises:
        Exception: User ID が取得できない場合
    """
    try:
        # API Gateway Cognito Authorizer から取得
        claims = event['requestContext']['authorizer']['claims']
        user_id = claims['sub']
        return user_id
    except (KeyError, TypeError) as e:
        raise Exception(f"Failed to get user ID from event: {str(e)}")


def select_query(question: str, user_id: str) -> str:
    """
    質問内容からクエリを選択（キーワードマッチング）

    Args:
        question: ユーザーの質問
        user_id: Cognito User ID

    Returns:
        SQL クエリ文字列
    """
    question_lower = question.lower()

    # サンプルクエリを取得
    queries = get_sample_queries(user_id)

    # キーワードマッチング
    if any(keyword in question_lower for keyword in ['most watched', '最も見', '一番見', 'よく見', 'top', 'チャンネル']):
        return queries['most_watched_channels']

    elif any(keyword in question_lower for keyword in ['total', '合計', '全部', '何本', '何件', 'how many']):
        return queries['total_videos']

    elif any(keyword in question_lower for keyword in ['recent', '最近', '直近', 'latest']):
        return queries['recent_history']

    elif any(keyword in question_lower for keyword in ['daily', '毎日', '日別', '推移']):
        return queries['daily_watch_count']

    else:
        # デフォルト: 最近の履歴を返す
        print("No keyword match, using default query (recent history)")
        return queries['recent_history']


def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """
    エラーレスポンスを生成

    Args:
        message: エラーメッセージ
        status_code: HTTP ステータスコード

    Returns:
        API Gateway レスポンス
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'error': message
        }, ensure_ascii=False)
    }
