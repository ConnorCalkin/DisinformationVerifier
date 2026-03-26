#get ecr repository URI
data "aws_ecr_repository" "rag_repo" {
  name = "c22-dv-rag-image"
}

#create lambda role

resource "aws_iam_role" "rag_lambda_role" {
    name = "c22-dv-rag-lambda-role"
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

resource "aws_iam_role_policy_attachment" "rag_lambda_logs" {
    role       = aws_iam_role.rag_lambda_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "rag_lambda_rds_access_policy" {
    name = "c22-dv-rag-lambda-rds-access-policy"

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

resource "aws_iam_policy" "rag_lambda_secrets_read_policy" {
    name = "c22-dv-rag-lambda-secrets-read-policy"

    policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Effect = "Allow",
                Action = [
                    "secretsmanager:GetSecretValue"
                ],
                Resource = aws_secretsmanager_secret.openai_key.arn
            }
        ]
    })
}

resource "aws_iam_role_policy_attachment" "rag_lambda_secrets_read" {
    role       = aws_iam_role.rag_lambda_role.name
    policy_arn = aws_iam_policy.rag_lambda_secrets_read_policy.arn
}

#create lambda function from image
resource "aws_lambda_function" "rag_lambda" {
    function_name = "c22-dv-rag-lambda"
    role          = aws_iam_role.rag_lambda_role.arn

    package_type = "Image"
    image_uri    = "${aws_ecr_repository.rag_repo.repository_url}@${data.aws_ecr_image.rag_lambda_image.id}"

    timeout      = 60
    memory_size  = 512

    environment {
        variables = {
            DB_HOST     = aws_db_instance.rds_instance.address
            DB_NAME     = var.db_name
            DB_USER     = var.db_username
            DB_PASSWORD = var.db_password
            SECRET_ID   = aws_secretsmanager_secret.openai_key.name
        }
    }
}