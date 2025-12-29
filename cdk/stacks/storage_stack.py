from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class StorageStack(Stack):
    """
    S3バケットスタック
    - jyoloyg-raw: JSONファイルアップロード先
    - jyoloyg-processed: Parquet形式の加工済みデータ
    - jyoloyg-athena-result: Athenaクエリ結果
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Raw Data Bucket - JSONファイルアップロード先
        self.raw_data_bucket = s3.Bucket(
            self,
            "RawDataBucket",
            bucket_name="jyoloyg-raw",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,  # 開発環境用：スタック削除時にバケットも削除
            auto_delete_objects=True,  # 開発環境用：バケット削除時にオブジェクトも削除
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter2Days",
                    enabled=True,
                    expiration=Duration.days(2),  # 2日後に自動削除（検証用）
                )
            ],
        )

        # 2. Processed Data Bucket - Parquet形式の加工済みデータ
        self.processed_data_bucket = s3.Bucket(
            self,
            "ProcessedDataBucket",
            bucket_name="jyoloyg-processed",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter2Days",
                    enabled=True,
                    expiration=Duration.days(2),  # 2日後に自動削除（検証用）
                )
            ],
        )

        # 3. Athena Results Bucket - Athenaクエリ結果
        self.athena_results_bucket = s3.Bucket(
            self,
            "AthenaResultsBucket",
            bucket_name="jyoloyg-athena-result",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter2Days",
                    enabled=True,
                    expiration=Duration.days(2),  # 2日後に削除（検証用）
                )
            ],
        )
