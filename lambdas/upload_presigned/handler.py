"""
S3署名付きURL生成Lambda関数

Phase 4.4で実装予定
"""


def lambda_handler(event, context):
    """
    Lambda handler
    TODO: Phase 4.4で実装
    """
    print("upload-presigned placeholder - To be implemented in Phase 4.4")
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"uploadUrl": "placeholder"}',
    }
