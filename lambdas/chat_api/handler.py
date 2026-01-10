"""
Athena + Bedrock + RAG 統合チャット API Lambda 関数

機能:
- Cognito User ID によるデータ分離
- ハイブリッドルーティング（Athena or RAG）
- Bedrock (Claude 3.5 Sonnet) による AI 分析
- CORS 対応
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

from clients.athena_client import AthenaClient, get_sample_queries
from clients.bedrock_client import BedrockClient
from clients.rag_client import RAGClient, format_rag_results
from shared.response import error, options, success

# 環境変数
ATHENA_DATABASE = os.environ.get("ATHENA_DATABASE", "youtube_analytics_db")
ATHENA_WORKGROUP = os.environ.get("ATHENA_WORKGROUP", "primary")
ATHENA_OUTPUT_LOCATION = os.environ.get("ATHENA_OUTPUT_LOCATION")
VECTORS_BUCKET = os.environ.get("VECTORS_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")


# クエリテンプレートのキーワードマッピング
QUERY_KEYWORDS = {
    "most_watched_channels": [
        "most watched",
        "最も見",
        "一番見",
        "よく見",
        "top",
        "お気に入り",
        "favorite",
    ],
    "total_videos": [
        "total",
        "合計",
        "全部",
        "何本",
        "何件",
        "how many",
        "いくつ",
        "数",
    ],
    "recent_history": ["recent", "最近", "直近", "latest", "この前", "昨日", "今日"],
    "daily_watch_count": ["daily", "毎日", "日別", "推移", "傾向", "trend", "グラフ"],
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler"""
    print(f"Event: {json.dumps(event)}")

    if event.get("httpMethod") == "OPTIONS":
        return options()

    try:
        user_id = get_user_id(event)
        print(f"User ID: {user_id}")

        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "").strip()

        if not question:
            return error("Question is required", 400)

        print(f"Question: {question}")

        # ルーティング判定
        query_type = detect_query_type(question)
        print(f"Query type: {query_type}")

        # Bedrock クライアント初期化
        bedrock_client = BedrockClient(
            region=AWS_REGION, max_tokens=2000, temperature=0.7
        )

        if query_type:
            # Athenaテンプレート使用
            answer, data_count = handle_athena_query(
                question, user_id, query_type, bedrock_client
            )
            source = "athena"
        else:
            # RAG検索使用
            answer, data_count = handle_rag_query(question, user_id, bedrock_client)
            source = "rag"

        return success({"answer": answer, "data_count": data_count, "source": source})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return error(f"Internal server error: {str(e)}", 500)


def detect_query_type(question: str) -> Optional[str]:
    """
    質問からクエリタイプを判定

    Returns:
        クエリタイプ名（該当なしの場合はNone → RAG使用）
    """
    question_lower = question.lower()

    for query_type, keywords in QUERY_KEYWORDS.items():
        if any(kw in question_lower for kw in keywords):
            return query_type

    return None  # RAG使用


def handle_athena_query(
    question: str, user_id: str, query_type: str, bedrock_client: BedrockClient
) -> Tuple[str, int]:
    """Athenaテンプレートで処理"""
    print(f"Using Athena template: {query_type}")

    athena_client = AthenaClient(
        database=ATHENA_DATABASE,
        output_location=ATHENA_OUTPUT_LOCATION,
        workgroup=ATHENA_WORKGROUP,
        region=AWS_REGION,
    )

    queries = get_sample_queries(user_id)
    query = queries.get(query_type, queries["recent_history"])

    data = athena_client.execute_query(query, use_cache=True, timeout=25)
    print(f"Athena returned {len(data)} rows")

    answer = bedrock_client.analyze_youtube_data(question=question, data=data)

    return answer, len(data)


def handle_rag_query(
    question: str, user_id: str, bedrock_client: BedrockClient
) -> Tuple[str, int]:
    """RAG検索で処理"""
    print("Using RAG search")

    if not VECTORS_BUCKET:
        # RAGが設定されていない場合はフォールバック
        print("VECTORS_BUCKET not set, falling back to recent history")
        return handle_athena_query(question, user_id, "recent_history", bedrock_client)

    rag_client = RAGClient(vectors_bucket=VECTORS_BUCKET, region=AWS_REGION)

    results = rag_client.search(query=question, user_id=user_id, top_k=20)

    if not results:
        print("No RAG results, falling back to recent history")
        return handle_athena_query(question, user_id, "recent_history", bedrock_client)

    # RAG結果をテキスト化
    context = format_rag_results(results)

    # Bedrockで回答生成
    answer = bedrock_client.chat(
        message=f"以下のYouTube視聴履歴データを参考に、質問に回答してください。\n\n{context}\n\n質問: {question}",
        system_prompt="あなたはYouTube視聴履歴の分析アシスタントです。提供されたデータに基づいて、ユーザーの質問に日本語で回答してください。",
    )

    return answer, len(results)


def get_user_id(event: Dict[str, Any]) -> str:
    """API Gateway イベントから Cognito User ID を取得"""
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
        return claims["sub"]
    except (KeyError, TypeError) as e:
        raise Exception(f"Failed to get user ID from event: {str(e)}")
