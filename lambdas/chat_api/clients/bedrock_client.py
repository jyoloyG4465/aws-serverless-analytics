"""
Bedrock クライアント - Claude 3.5 Sonnet による AI 分析

機能:
- Bedrock API を使った Claude 3.5 Sonnet の呼び出し
- YouTube 閲覧履歴データの分析
- エラーハンドリングとリトライ
"""
import boto3
import json
from typing import Dict, Any, List, Optional


class BedrockClient:
    """Bedrock Claude 3.5 Sonnet クライアント"""

    def __init__(
        self,
        region: str = 'ap-northeast-1',
        model_id: str = 'anthropic.claude-3-5-sonnet-20240620-v1:0',
        max_tokens: int = 2000,
        temperature: float = 0.7
    ):
        """
        Args:
            region: AWS リージョン（ap-northeast-1 で Claude 3.5 Sonnet 利用可能）
            model_id: Bedrock モデル ID (ON_DEMAND対応版)
            max_tokens: 最大トークン数（コスト最適化）
            temperature: 生成のランダム性（0.0-1.0）
        """
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature

    def analyze_youtube_data(
        self,
        question: str,
        data: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        YouTube 閲覧履歴データを分析して質問に回答

        Args:
            question: ユーザーの質問
            data: Athena クエリ結果（辞書のリスト）
            system_prompt: システムプロンプト（オプション）

        Returns:
            Claude の回答テキスト

        Raises:
            Exception: API 呼び出し失敗時
        """
        # デフォルトのシステムプロンプト
        if not system_prompt:
            system_prompt = """あなたはYouTube閲覧履歴データの分析専門家です。
ユーザーから提供されたデータに基づいて、具体的で役立つ分析結果を提供してください。
数値は正確に、傾向は客観的に分析してください。
日本語で回答してください。"""

        # ユーザープロンプト構築
        user_prompt = self._build_user_prompt(question, data)

        print(f"Calling Bedrock API with model: {self.model_id}")
        print(f"Question: {question}")
        print(f"Data rows: {len(data)}")

        try:
            # Bedrock API 呼び出し
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                })
            )

            # レスポンスパース
            response_body = json.loads(response['body'].read())

            # Claude の回答を取得
            if 'content' in response_body and len(response_body['content']) > 0:
                answer = response_body['content'][0]['text']
                print(f"Response received: {len(answer)} characters")
                return answer
            else:
                raise Exception("No content in Bedrock response")

        except Exception as e:
            print(f"Bedrock API error: {str(e)}")
            raise

    def _build_user_prompt(
        self,
        question: str,
        data: List[Dict[str, Any]]
    ) -> str:
        """
        ユーザープロンプトを構築

        Args:
            question: ユーザーの質問
            data: データ（辞書のリスト）

        Returns:
            プロンプト文字列
        """
        # データを読みやすい形式に整形
        if not data:
            data_text = "データがありません。まだYouTube閲覧履歴がアップロードされていないようです。"
        else:
            # 最初の数件をサンプル表示（全データだとトークン超過の可能性）
            sample_size = min(len(data), 50)
            data_text = json.dumps(data[:sample_size], ensure_ascii=False, indent=2)

            # データ件数を明記
            if len(data) > sample_size:
                data_text += f"\n\n（全{len(data)}件中、最初の{sample_size}件を表示）"

        prompt = f"""以下のYouTube閲覧履歴データに基づいて質問に答えてください。

データ:
{data_text}

質問: {question}

データに基づいた具体的な回答を提供してください。
数値やチャンネル名など、データから読み取れる情報を含めてください。"""

        return prompt

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        会話形式でチャット（履歴対応）

        Args:
            message: ユーザーメッセージ
            conversation_history: 会話履歴（[{"role": "user", "content": "..."}] 形式）
            system_prompt: システムプロンプト

        Returns:
            Claude の回答
        """
        if not system_prompt:
            system_prompt = """あなたは親切なアシスタントです。
ユーザーの質問に対して、簡潔で分かりやすい回答を提供してください。
日本語で回答してください。"""

        # 会話履歴を構築
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": message
        })

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "system": system_prompt,
                    "messages": messages
                })
            )

            response_body = json.loads(response['body'].read())

            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            else:
                raise Exception("No content in Bedrock response")

        except Exception as e:
            print(f"Bedrock chat error: {str(e)}")
            raise


def format_data_summary(data: List[Dict[str, Any]]) -> str:
    """
    データの要約を生成（プロンプトに含める用）

    Args:
        data: クエリ結果データ

    Returns:
        要約テキスト
    """
    if not data:
        return "データなし"

    summary = f"データ件数: {len(data)}件\n"

    # 最初の数件をサンプル表示
    sample_size = min(len(data), 5)
    summary += f"\nサンプル（最初の{sample_size}件）:\n"

    for i, row in enumerate(data[:sample_size], 1):
        summary += f"{i}. "
        summary += ", ".join([f"{k}: {v}" for k, v in row.items()])
        summary += "\n"

    return summary
