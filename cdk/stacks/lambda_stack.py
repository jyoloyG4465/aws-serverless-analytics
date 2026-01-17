from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_glue as glue
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
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
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 共通 Lambda Layer（レスポンスヘルパーなど）
        self.shared_layer = lambda_.LayerVersion(
            self,
            "SharedLayer",
            layer_version_name="youtube-analytics-shared",
            code=lambda_.Code.from_asset("../lambdas/shared"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared utilities for Lambda functions",
        )

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
            layers=[self.shared_layer],
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
            layers=[self.shared_layer],
            timeout=Duration.seconds(29),  # API Gateway制限
            memory_size=1024,
            environment={
                "ATHENA_DATABASE": database_name,
                "ATHENA_WORKGROUP": workgroup_name,
                "ATHENA_OUTPUT_LOCATION": f"s3://{athena_results_bucket.bucket_name}/results/",
                "VECTORS_BUCKET": processed_bucket.bucket_name,
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
                    f"arn:aws:athena:{self.region}:{self.account}:workgroup/{workgroup_name}",
                    f"arn:aws:athena:{self.region}:{self.account}:datacatalog/*",
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

        # Bedrock呼び出し権限（Claude 3.5 Sonnet + Titan Embeddings）
        self.chat_api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1",
                ],
            )
        )

        # AWS Marketplace権限（Bedrockモデルアクセスに必要）
        self.chat_api_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "aws-marketplace:ViewSubscriptions",
                    "aws-marketplace:Subscribe",
                ],
                resources=["*"],
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
            layers=[self.shared_layer],
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

        # 4. Vectorize Lambda関数（RAG用ベクトル化）
        vectorize_log_group = logs.LogGroup(
            self,
            "VectorizeLogGroup",
            log_group_name="/aws/lambda/youtube-analytics-vectorize",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # AWS SDK for pandas Layer（pandas, pyarrow含む）
        pandas_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "PandasLayer",
            f"arn:aws:lambda:{self.region}:336392948345:layer:AWSSDKPandas-Python311:19",
        )

        self.vectorize_function = lambda_.Function(
            self,
            "VectorizeFunction",
            function_name="youtube-analytics-vectorize",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/vectorize"),
            layers=[self.shared_layer, pandas_layer],
            timeout=Duration.minutes(10),  # 4000件ベクトル化対応
            memory_size=1024,
            environment={
                "VECTORS_BUCKET": processed_bucket.bucket_name,
            },
            description="Vectorize YouTube history for RAG",
            log_group=vectorize_log_group,
        )

        # S3読み書き権限
        processed_bucket.grant_read_write(self.vectorize_function)

        # Bedrock Embeddings権限
        self.vectorize_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1"
                ],
            )
        )

        # EventBridgeルールでParquet作成をトリガー
        parquet_event_rule = events.Rule(
            self,
            "ParquetCreatedRule",
            description="Trigger vectorize when Parquet is created",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [processed_bucket.bucket_name]},
                    "object": {
                        "key": [{"prefix": "processed/"}, {"suffix": ".parquet"}]
                    },
                },
            ),
        )
        parquet_event_rule.add_target(targets.LambdaFunction(self.vectorize_function))

        # 5. Check Data Status Lambda関数
        check_data_status_log_group = logs.LogGroup(
            self,
            "CheckDataStatusLogGroup",
            log_group_name="/aws/lambda/youtube-analytics-check-data-status",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_WEEK,
        )

        self.check_data_status_function = lambda_.Function(
            self,
            "CheckDataStatusFunction",
            function_name="youtube-analytics-check-data-status",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/check_data_status"),
            layers=[self.shared_layer],
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={
                "VECTORS_BUCKET": processed_bucket.bucket_name,
            },
            description="Check if user's vector data exists in S3",
            log_group=check_data_status_log_group,
        )

        # S3読み取り権限（head_objectに必要）
        processed_bucket.grant_read(self.check_data_status_function)
