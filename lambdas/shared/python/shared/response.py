"""
Lambda API レスポンスヘルパー
"""
import json
from typing import Any, Dict, Optional

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
}


def success(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """成功レスポンスを生成"""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(data, ensure_ascii=False)
    }


def error(message: str, status_code: int = 400, details: Optional[str] = None) -> Dict[str, Any]:
    """エラーレスポンスを生成"""
    body: Dict[str, Any] = {'error': message}
    if details:
        body['details'] = details
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, ensure_ascii=False)
    }


def options() -> Dict[str, Any]:
    """CORS プリフライトレスポンスを生成"""
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': ''
    }
