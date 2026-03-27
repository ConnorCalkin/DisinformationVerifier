resource "aws_iam_role" "rds_connect_lambda_role" {
    name = "c22-dv-rds-connect-lambda-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Action = "sts:AssumeRole",
                Effect = "Allow",
                Principal = {
                    Service = "lambda.amazonaws.com"
                }
            }
        ]
    })
}

resource "aws_iam_policy" "rds_connect_rds_access_policy" {
    name = "c22-dv-rds-connect-rds-access-policy"

    policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Effect = "Allow",
                Action = [
                    "rds-db:connect"
                ],
                Resource = "*"
            }
        ]
    })
}

resource "aws_iam_policy" "rds_connect_lambda_secrets_read_policy" {
    name = "c22-dv-rds-connect-lambda-secrets-read-policy"

    policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Effect = "Allow",
                Action = [
                    "secretsmanager:GetSecretValue"
                ],
                Resource = aws_secretsmanager_secret.credentials.arn
            }
        ]
    })
}

resource "aws_iam_role_policy_attachment" "rds_connect_lambda_secrets_read" {
    role       = aws_iam_role.rds_connect_lambda_role.name
    policy_arn = aws_iam_policy.rds_connect_lambda_secrets_read_policy.arn
}

resource "aws_iam_role_policy_attachment" "rds_connect_lambda_logs" {
    role       = aws_iam_role.rds_connect_lambda_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "rds_connect_lambda_rds_access" {
    role       = aws_iam_role.rds_connect_lambda_role.name
    policy_arn = aws_iam_policy.rds_connect_rds_access_policy.arn
}