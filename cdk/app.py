#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.glue_stack import GlueStack
from stacks.athena_stack import AthenaStack


app = cdk.App()

# 環境設定
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
)

# Storage Stack (S3バケット)
storage_stack = StorageStack(
    app,
    "YoutubeAnalyticsStorageStack",
    env=env,
    description="S3 buckets for YouTube analytics data storage"
)

# Glue Stack (データ処理ジョブ)
glue_stack = GlueStack(
    app,
    "YoutubeAnalyticsGlueStack",
    raw_bucket=storage_stack.raw_data_bucket,
    processed_bucket=storage_stack.processed_data_bucket,
    env=env,
    description="Glue Python Shell job for data processing"
)
glue_stack.add_dependency(storage_stack)

# Athena Stack (データベース、テーブル、ワークグループ)
athena_stack = AthenaStack(
    app,
    "YoutubeAnalyticsAthenaStack",
    processed_bucket=storage_stack.processed_data_bucket,
    athena_results_bucket=storage_stack.athena_results_bucket,
    env=env,
    description="Athena workgroup and table definitions"
)
athena_stack.add_dependency(storage_stack)

app.synth()
