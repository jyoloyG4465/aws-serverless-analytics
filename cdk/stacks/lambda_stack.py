from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_glue as glue,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    Duration,
)
from constructs import Construct


class LambdaStack(Stack):
    """
    Lambda関数スタック
    - trigger-glue: S3イベントでGlueジョブ起動
    - chat-api: Athena + Bedrock統合
    - upload-presigned: S3署名付きURL生成
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        raw_bucket: s3.IBucket,
        processed_bucket: s3.IBucket,
        athena_results_bucket: s3.IBucket,
        glue_job: glue.CfnJob,
        database_name: str,
        workgroup_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Trigger Glue Lambda関数
        # ロググループを明示的に作成（cdk destroyで自動削除されるように）
        trigger_glue_log_group = logs.LogGroup(
            self,
            "TriggerGlueLogGroup",
            log_group_name="/aws/lambda/youtube-analytics-trigger-glue",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
        )

        self.trigger_glue_function = lambda_.Function(
            self,
            "TriggerGlueFunction",
            function_name="youtube-analytics-trigger-glue",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/trigger_glue"),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "GLUE_JOB_NAME": glue_job.name,
                "OUTPUT_BUCKET": processed_bucket.bucket_name,
            },
            description="Trigger Glue job on S3 upload",
            log_group=trigger_glue_log_group,
        )

        # Glueジョブ起動権限
        self.trigger_glue_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["glue:StartJobRun"],
                resources=[
                    f"arn:aws:glue:{self.region}:{self.account}:job/{glue_job.name}"
                ],
            )
        )

        # S3読み取り権限
        raw_bucket.grant_read(self.trigger_glue_function)

        # EventBridgeルールでS3イベントを検知してLambdaをトリガー（循環依存回避）
        s3_event_rule = events.Rule(
            self,
            "S3JsonObjectCreatedRule",
            description="Trigger Glue job when JSON file is uploaded to S3",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [raw_bucket.bucket_name]},
                    "object": {"key": [{"suffix": ".json"}]},
                },
            ),
        )
        s3_event_rule.add_target(targets.LambdaFunction(self.trigger_glue_function))

        # 2. Chat API Lambda関数
        # ロググループを明示的に作成（cdk destroyで自動削除されるように）
        chat_api_log_group = logs.LogGroup(
            self,
            "ChatApiLogGroup",
            log_group_name="/aws/lambda/youtube-analytics-chat-api",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
        )

        self.chat_api_function = lambda_.Function(
            self,
            "ChatApiFunction",
            function_name="youtube-analytics-chat-api",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/chat_api"),
            timeout=Duration.seconds(29),  # API Gateway制限
            memory_size=512,
            environment={
                "ATHENA_DATABASE": database_name,
                "ATHENA_WORKGROUP": workgroup_name,
                "ATHENA_OUTPUT_LOCATION": f"s3://{athena_results_bucket.bucket_name}/results/",
            },
            description="Chat API with Athena and Bedrock integration",
            log_group=chat_api_log_group,
        )

        # Athena実行権限
        self.chat_api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                    "athena:StopQueryExecution",
                ],
                resources=[
                    f"arn:aws:athena:{self.region}:{self.account}:workgroup/{workgroup_name}"
                ],
            )
        )

        # Glue Data Catalog読み取り権限
        self.chat_api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetPartitions",
                ],
                resources=[
                    f"arn:aws:glue:{self.region}:{self.account}:catalog",
                    f"arn:aws:glue:{self.region}:{self.account}:database/{database_name}",
                    f"arn:aws:glue:{self.region}:{self.account}:table/{database_name}/*",
                ],
            )
        )

        # S3読み書き権限（Athena結果、処理済みデータ）
        processed_bucket.grant_read(self.chat_api_function)
        athena_results_bucket.grant_read_write(self.chat_api_function)

        # Bedrock呼び出し権限（ap-northeast-1でClaude 3.5 Sonnet利用可能）
        self.chat_api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
                ],
            )
        )

        # 3. Upload Presigned URL Lambda関数
        # ロググループを明示的に作成（cdk destroyで自動削除されるように）
        upload_presigned_log_group = logs.LogGroup(
            self,
            "UploadPresignedLogGroup",
            log_group_name="/aws/lambda/youtube-analytics-upload-presigned",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
        )

        self.upload_presigned_function = lambda_.Function(
            self,
            "UploadPresignedFunction",
            function_name="youtube-analytics-upload-presigned",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/upload_presigned"),
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={
                "RAW_BUCKET": raw_bucket.bucket_name,
            },
            description="Generate S3 presigned URL for file upload",
            log_group=upload_presigned_log_group,
        )

        # S3書き込み権限
        raw_bucket.grant_put(self.upload_presigned_function)
