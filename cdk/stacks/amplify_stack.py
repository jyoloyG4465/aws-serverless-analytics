from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_amplify as amplify,
    CfnOutput,
)
from constructs import Construct
import os
import json


class AmplifyStack(Stack):
    """
    Amplify Hostingスタック
    - Next.jsフロントエンドのホスティング
    - 環境変数設定
    - ビルド設定

    注意: GitHubリポジトリ連携は手動でセットアップする必要があります
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool_id: str,
        user_pool_client_id: str,
        api_endpoint: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ビルド設定
        build_spec = {
            "version": "1.0",
            "frontend": {
                "phases": {
                    "preBuild": {
                        "commands": [
                            "cd frontend",
                            "npm ci",
                        ]
                    },
                    "build": {
                        "commands": [
                            "npm run build",
                        ]
                    },
                },
                "artifacts": {
                    "baseDirectory": "frontend/.next",
                    "files": ["**/*"],
                },
                "cache": {
                    "paths": ["frontend/node_modules/**/*"],
                },
            },
        }

        # Amplifyアプリ作成（L1コンストラクト使用）
        self.amplify_app = amplify.CfnApp(
            self,
            "YoutubeAnalyticsAmplifyApp",
            name="youtube-analytics-frontend",
            description="YouTube Analytics Next.js Frontend",
            # 環境変数
            environment_variables=[
                amplify.CfnApp.EnvironmentVariableProperty(
                    name="NEXT_PUBLIC_USER_POOL_ID",
                    value=user_pool_id,
                ),
                amplify.CfnApp.EnvironmentVariableProperty(
                    name="NEXT_PUBLIC_USER_POOL_CLIENT_ID",
                    value=user_pool_client_id,
                ),
                amplify.CfnApp.EnvironmentVariableProperty(
                    name="NEXT_PUBLIC_API_ENDPOINT",
                    value=api_endpoint,
                ),
                amplify.CfnApp.EnvironmentVariableProperty(
                    name="NEXT_PUBLIC_AWS_REGION",
                    value=self.region,
                ),
                amplify.CfnApp.EnvironmentVariableProperty(
                    name="_LIVE_UPDATES",
                    value='[{"pkg":"next","type":"internal","version":"14"}]',
                ),
            ],
            # ビルド設定
            build_spec=json.dumps(build_spec),
            # プラットフォーム
            platform="WEB_COMPUTE",
        )
        # スタック削除時にAmplifyアプリも削除
        self.amplify_app.apply_removal_policy(RemovalPolicy.DESTROY)

        # mainブランチ設定
        self.main_branch = amplify.CfnBranch(
            self,
            "MainBranch",
            app_id=self.amplify_app.attr_app_id,
            branch_name="main",
            stage="PRODUCTION",
            enable_auto_build=True,
        )
        # スタック削除時にブランチも削除
        self.main_branch.apply_removal_policy(RemovalPolicy.DESTROY)

        # 出力
        CfnOutput(
            self,
            "AmplifyAppId",
            value=self.amplify_app.attr_app_id,
            description="Amplify App ID (Setup GitHub connection manually in AWS Console)",
        )

        CfnOutput(
            self,
            "AmplifyDefaultDomain",
            value=self.amplify_app.attr_default_domain,
            description="Amplify Default Domain",
        )
