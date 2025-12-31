"""
Athena クライアント - クエリ実行とキャッシング機能

機能:
- Athena クエリ実行と結果取得
- メモリ内キャッシング（Lambda 暖機時に有効）
- タイムアウト処理
- エラーハンドリング
"""
import boto3
import time
from typing import List, Dict, Any, Optional
import hashlib
import json

# Lambda暖機時にキャッシュを保持
QUERY_CACHE = {}
CACHE_TTL = 300  # 5分間キャッシュ


class AthenaClient:
    """Athena クエリ実行とキャッシング"""

    def __init__(
        self,
        database: str,
        output_location: str,
        workgroup: str = 'primary',
        region: str = 'ap-northeast-1'
    ):
        """
        Args:
            database: Athena データベース名
            output_location: クエリ結果の出力先 S3 パス
            workgroup: Athena ワークグループ名
            region: AWS リージョン
        """
        self.client = boto3.client('athena', region_name=region)
        self.database = database
        self.output_location = output_location
        self.workgroup = workgroup

    def execute_query(
        self,
        query: str,
        use_cache: bool = True,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Athena クエリを実行して結果を取得

        Args:
            query: SQL クエリ文字列
            use_cache: キャッシュを使用するか
            timeout: タイムアウト秒数

        Returns:
            クエリ結果のリスト（辞書形式）

        Raises:
            Exception: クエリ実行失敗時
        """
        # キャッシュキー生成
        cache_key = self._generate_cache_key(query)

        # キャッシュチェック
        if use_cache and cache_key in QUERY_CACHE:
            cached_result = QUERY_CACHE[cache_key]
            # TTL チェック
            if time.time() - cached_result['timestamp'] < CACHE_TTL:
                print(f"Cache hit for query: {query[:50]}...")
                return cached_result['data']
            else:
                # 期限切れキャッシュを削除
                del QUERY_CACHE[cache_key]

        print(f"Executing query: {query[:100]}...")

        # クエリ実行
        try:
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': self.database},
                ResultConfiguration={'OutputLocation': self.output_location},
                WorkGroup=self.workgroup
            )

            query_execution_id = response['QueryExecutionId']
            print(f"Query execution ID: {query_execution_id}")

            # クエリ完了を待機
            result = self._wait_for_query_completion(query_execution_id, timeout)

            # 結果をキャッシュ
            if use_cache:
                QUERY_CACHE[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }

            return result

        except Exception as e:
            print(f"Query execution failed: {str(e)}")
            raise

    def _wait_for_query_completion(
        self,
        query_execution_id: str,
        timeout: int
    ) -> List[Dict[str, Any]]:
        """
        クエリ完了を待機して結果を取得

        Args:
            query_execution_id: クエリ実行 ID
            timeout: タイムアウト秒数

        Returns:
            クエリ結果

        Raises:
            Exception: クエリ失敗またはタイムアウト時
        """
        start_time = time.time()

        while True:
            # タイムアウトチェック
            if time.time() - start_time > timeout:
                raise Exception(f"Query timeout after {timeout} seconds")

            # クエリステータス確認
            response = self.client.get_query_execution(
                QueryExecutionId=query_execution_id
            )

            status = response['QueryExecution']['Status']['State']

            if status == 'SUCCEEDED':
                # 結果取得
                return self._get_query_results(query_execution_id)

            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get(
                    'StateChangeReason',
                    'Unknown error'
                )
                raise Exception(f"Query {status}: {reason}")

            # QUEUED または RUNNING の場合は待機
            time.sleep(1)

    def _get_query_results(
        self,
        query_execution_id: str,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        クエリ結果を取得してパース

        Args:
            query_execution_id: クエリ実行 ID
            max_results: 最大結果件数

        Returns:
            クエリ結果のリスト
        """
        results = []
        next_token = None

        while True:
            # ページング対応
            params = {
                'QueryExecutionId': query_execution_id,
                'MaxResults': max_results
            }

            if next_token:
                params['NextToken'] = next_token

            response = self.client.get_query_results(**params)

            # ヘッダー行を取得（最初のページのみ）
            if not results:
                rows = response['ResultSet']['Rows']
                if not rows:
                    return []

                # カラム名取得
                headers = [col['VarCharValue'] for col in rows[0]['Data']]

                # データ行をパース（ヘッダー行をスキップ）
                for row in rows[1:]:
                    results.append(self._parse_row(row, headers))
            else:
                # 2ページ目以降はヘッダーなし
                for row in response['ResultSet']['Rows']:
                    results.append(self._parse_row(row, headers))

            # 次ページがあるかチェック
            next_token = response.get('NextToken')
            if not next_token:
                break

        print(f"Retrieved {len(results)} rows")
        return results

    def _parse_row(
        self,
        row: Dict[str, Any],
        headers: List[str]
    ) -> Dict[str, Any]:
        """
        Athena の行データを辞書形式にパース

        Args:
            row: Athena の行データ
            headers: カラム名リスト

        Returns:
            パースされた辞書
        """
        parsed = {}

        for i, col in enumerate(row['Data']):
            key = headers[i]
            # VarCharValue が存在する場合は値を取得、なければ NULL
            value = col.get('VarCharValue')
            parsed[key] = value

        return parsed

    def _generate_cache_key(self, query: str) -> str:
        """
        クエリ文字列からキャッシュキーを生成

        Args:
            query: SQL クエリ

        Returns:
            SHA256 ハッシュ
        """
        return hashlib.sha256(query.encode()).hexdigest()

    def clear_cache(self):
        """キャッシュをクリア"""
        global QUERY_CACHE
        QUERY_CACHE = {}
        print("Query cache cleared")


def get_sample_queries(user_id: str) -> Dict[str, str]:
    """
    よく使うクエリのテンプレート

    Args:
        user_id: Cognito User ID

    Returns:
        クエリ名とSQL文字列の辞書
    """
    return {
        'most_watched_channels': f"""
            SELECT channel_name, COUNT(*) as watch_count
            FROM youtube_watch_history
            WHERE user_id = '{user_id}'
            GROUP BY channel_name
            ORDER BY watch_count DESC
            LIMIT 10
        """,

        'total_videos': f"""
            SELECT COUNT(*) as total
            FROM youtube_watch_history
            WHERE user_id = '{user_id}'
        """,

        'recent_history': f"""
            SELECT title, channel_name, watched_at
            FROM youtube_watch_history
            WHERE user_id = '{user_id}'
            ORDER BY watched_at DESC
            LIMIT 100
        """,

        'daily_watch_count': f"""
            SELECT
                DATE(CAST(watched_at AS TIMESTAMP)) as watch_date,
                COUNT(*) as count
            FROM youtube_watch_history
            WHERE user_id = '{user_id}'
            GROUP BY DATE(CAST(watched_at AS TIMESTAMP))
            ORDER BY watch_date DESC
            LIMIT 30
        """
    }
