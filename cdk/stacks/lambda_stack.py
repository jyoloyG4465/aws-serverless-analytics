from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_glue as glue,
    aws_s3_notifications as s3n,
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

        # S3イベント通知設定（JSONファイルアップロード時にトリガー）
        raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.trigger_glue_function),
            s3.NotificationKeyFilter(suffix=".json"),
        )

        # 2. Chat API Lambda関数
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
                "ATHENA_OUTPUT_BUCKET": athena_results_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "BEDROCK_REGION": "us-east-1",
            },
            description="Chat API with Athena and Bedrock integration",
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

        # Bedrock呼び出し権限
        self.chat_api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
                ],
            )
        )

        # 3. Upload Presigned URL Lambda関数
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
        )

        # S3書き込み権限
        raw_bucket.grant_put(self.upload_presigned_function)
