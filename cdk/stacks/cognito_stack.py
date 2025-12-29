from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class CognitoStack(Stack):
    """
    Cognitoユーザープールスタック
    - メールサインイン
    - 管理者によるユーザー作成のみ（セルフサインアップ無効）
    - パスワードポリシー設定
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Cognitoユーザープール
        self.user_pool = cognito.UserPool(
            self,
            "YoutubeAnalyticsUserPool",
            user_pool_name="youtube-analytics-user-pool",
            # メールサインイン
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False,
            ),
            # セルフサインアップ無効（管理者のみユーザー作成可能）
            self_sign_up_enabled=False,
            # パスワードポリシー
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            # MFA設定（オプショナル、個人利用のため無効化）
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=False,
                otp=True,
            ),
            # アカウント復旧設定
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            # メール設定（デフォルトのCognito送信）
            email=cognito.UserPoolEmail.with_cognito(),
            # ユーザー検証（メールのみ）
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            # 標準属性
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=False,
                ),
            ),
            # スタック削除時にユーザープールも削除（検証環境用）
            removal_policy=RemovalPolicy.DESTROY,
        )

        # UserPoolClient（フロントエンド用）
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "YoutubeAnalyticsUserPoolClient",
            user_pool_client_name="youtube-analytics-web-client",
            user_pool=self.user_pool,
            # 認証フロー設定
            auth_flows=cognito.AuthFlow(
                user_password=True,  # ユーザー名・パスワード認証
                user_srp=True,  # SRP認証（推奨）
            ),
            # OAuth設定（将来的なソーシャルログイン用）
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False,
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
            ),
            # トークン有効期限
            access_token_validity=cognito.Duration.hours(1),
            id_token_validity=cognito.Duration.hours(1),
            refresh_token_validity=cognito.Duration.days(30),
            # クライアントシークレット不要（パブリッククライアント）
            generate_secret=False,
        )

        # 出力
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
        )
