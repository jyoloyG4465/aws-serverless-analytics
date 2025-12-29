#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.storage_stack import StorageStack


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

app.synth()
