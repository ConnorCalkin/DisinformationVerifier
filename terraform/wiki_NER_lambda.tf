resource "aws_lambda_function_url" "wiki_ner_lambda_url" {
  function_name      = aws_lambda_function.wiki_ner_lambda.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "allow_public_access_wiki_ner_lambda" {
  statement_id           = "AllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.wiki_ner_lambda.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function" "wiki_ner_lambda" {
    function_name = "c22-dv-wiki-ner-lambda"
    role          = aws_iam_role.lambda_role.arn

    package_type = "Image"
    image_uri    = "${aws_ecr_repository.wiki_ner_repo.repository_url}@${data.aws_ecr_image.wiki_ner_lambda_image.id}"

    timeout      = 60
    memory_size  = 512

    environment {
        variables = {
            SECRET_ID = aws_secretsmanager_secret.credentials.name
        }
    }
}

resource "aws_iam_role" "lambda_role" {
    name = "c22-dv-wiki-ner-lambda-role"
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

resource "aws_iam_role_policy_attachment" "lambda_logs" {
    role       = aws_iam_role.lambda_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_secrets_read" {
    name = "c22-dv-lambda-secrets-read-policy"
    role = aws_iam_role.lambda_role.id

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
