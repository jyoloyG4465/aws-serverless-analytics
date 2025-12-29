from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    CfnOutput,
)
from constructs import Construct


class ApiGatewayStack(Stack):
    """
    API Gatewayスタック
    - REST API定義
    - Cognito Authorizer設定
    - Lambda統合（chat-api, upload-presigned）
    - CORS設定
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool: cognito.IUserPool,
        chat_api_function: lambda_.IFunction,
        upload_presigned_function: lambda_.IFunction,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # REST API作成
        self.api = apigw.RestApi(
            self,
            "YoutubeAnalyticsApi",
            rest_api_name="youtube-analytics-api",
            description="YouTube Analytics API with Cognito authentication",
            # CORS設定
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,  # 本番環境では特定ドメインに制限
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
                allow_credentials=True,
            ),
            # デプロイ設定
            deploy=True,
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
        )

        # Cognito Authorizer作成
        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="youtube-analytics-authorizer",
            identity_source="method.request.header.Authorization",
        )

        # /chat エンドポイント（チャットAPI）
        chat_resource = self.api.root.add_resource("chat")
        chat_integration = apigw.LambdaIntegration(
            chat_api_function,
            proxy=True,
            integration_responses=[
                apigw.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                    },
                )
            ],
        )
        chat_resource.add_method(
            "POST",
            chat_integration,
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                )
            ],
        )

        # /upload エンドポイント（署名付きURL取得）
        upload_resource = self.api.root.add_resource("upload")
        upload_integration = apigw.LambdaIntegration(
            upload_presigned_function,
            proxy=True,
            integration_responses=[
                apigw.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                    },
                )
            ],
        )
        upload_resource.add_method(
            "POST",
            upload_integration,
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                )
            ],
        )

        # API URLを出力
        self.api_url = self.api.url

        CfnOutput(
            self,
            "ApiEndpoint",
            value=self.api.url,
            description="API Gateway Endpoint URL",
        )
