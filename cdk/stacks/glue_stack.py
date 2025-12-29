from aws_cdk import (
    Stack,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct


class GlueStack(Stack):
    """
    AWS Glue Python Shellジョブスタック
    YouTube履歴JSONをParquet形式に変換
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        raw_bucket: s3.IBucket,
        processed_bucket: s3.IBucket,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Glueジョブ用のIAMロール
        glue_role = iam.Role(
            self,
            "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )

        # S3バケットへの読み書き権限
        raw_bucket.grant_read(glue_role)
        processed_bucket.grant_write(glue_role)

        # CloudWatch Logsへの書き込み権限
        glue_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Glueスクリプト用のS3バケット
        script_bucket = s3.Bucket(
            self,
            "GlueScriptBucket",
            bucket_name="jyoloyg-glue-scripts",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # Glueスクリプトをデプロイ
        s3deploy.BucketDeployment(
            self,
            "DeployGlueScript",
            sources=[s3deploy.Source.asset("../glue_jobs")],
            destination_bucket=script_bucket,
            destination_key_prefix="scripts",
        )

        # Glue Python Shellジョブ定義
        self.glue_job = glue.CfnJob(
            self,
            "ProcessYoutubeHistoryJob",
            name="process-youtube-history",
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="pythonshell",  # Python Shell（PySpark不使用）
                python_version="3.9",
                script_location=f"s3://{script_bucket.bucket_name}/scripts/process_youtube_history.py",
            ),
            default_arguments={
                "--TempDir": f"s3://{script_bucket.bucket_name}/temp/",
                "--job-language": "python",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                # 外部Pythonライブラリの指定
                "--additional-python-modules": "pandas==2.0.3,pyarrow==12.0.1",
            },
            max_capacity=1.0,  # 1 DPU（最小）
            timeout=10,  # 10分
            glue_version="3.0",
            description="Process YouTube watch history JSON to Parquet format",
        )
