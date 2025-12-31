from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_athena as athena,
    aws_glue as glue,
    aws_s3 as s3,
)
from constructs import Construct


class AthenaStack(Stack):
    """
    Amazon Athenaワークグループとテーブル定義スタック
    YouTube閲覧履歴データをクエリ可能にする
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        processed_bucket: s3.IBucket,
        athena_results_bucket: s3.IBucket,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Glue Data Catalogデータベース
        self.database = glue.CfnDatabase(
            self,
            "YoutubeAnalyticsDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="youtube_analytics_db",
                description="YouTube watch history analytics database",
            ),
        )
        # スタック削除時にデータベースも削除
        self.database.apply_removal_policy(RemovalPolicy.DESTROY)

        # Athenaワークグループ
        self.workgroup = athena.CfnWorkGroup(
            self,
            "YoutubeAnalyticsWorkGroup",
            name="youtube-analytics-workgroup",
            description="Workgroup for YouTube analytics queries",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results_bucket.bucket_name}/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3"
                    ),
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
                engine_version=athena.CfnWorkGroup.EngineVersionProperty(
                    selected_engine_version="Athena engine version 3"
                ),
            ),
        )
        # スタック削除時にワークグループも削除
        self.workgroup.apply_removal_policy(RemovalPolicy.DESTROY)

        # YouTube閲覧履歴テーブル定義（user_idパーティションのみ）
        self.table = glue.CfnTable(
            self,
            "YoutubeWatchHistoryTable",
            catalog_id=self.account,
            database_name=self.database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name="youtube_watch_history",
                description="YouTube watch history data with user partitioning",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "EXTERNAL": "TRUE",
                    "parquet.compression": "SNAPPY",
                    "projection.enabled": "true",
                    # user_id projection (injected - ユーザーごとに動的に指定)
                    "projection.user_id.type": "injected",
                    # storage location template
                    "storage.location.template": f"s3://{processed_bucket.bucket_name}/processed/${{user_id}}/",
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(
                            name="title",
                            type="string",
                            comment="Video title",
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="video_id",
                            type="string",
                            comment="YouTube video ID",
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="channel_name",
                            type="string",
                            comment="Channel name",
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="channel_id",
                            type="string",
                            comment="YouTube channel ID",
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="watched_at",
                            type="string",
                            comment="Watch timestamp (temporarily string for compatibility)",
                        ),
                    ],
                    location=f"s3://{processed_bucket.bucket_name}/processed/",
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                        parameters={
                            "serialization.format": "1",
                        },
                    ),
                ),
                partition_keys=[
                    glue.CfnTable.ColumnProperty(
                        name="user_id",
                        type="string",
                        comment="Cognito User ID for data isolation",
                    ),
                ],
            ),
        )

        # テーブルはデータベースに依存
        self.table.add_dependency(self.database)
        # スタック削除時にテーブルも削除
        self.table.apply_removal_policy(RemovalPolicy.DESTROY)
