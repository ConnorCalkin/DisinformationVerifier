resource "aws_ecr_repository" "llm-interaction-repo" {
  name                 = "c22-dv-llm-interaction-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

data "aws_ecr_image" "llm_interaction_image" {
  repository_name = aws_ecr_repository.llm-interaction-repo.name
  image_tag       = "latest"
}

# The Execution Role - Renamed to be unique
resource "aws_iam_role" "iam_for_llm_lambda" {
  name = "c22-dv-llm-interaction-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_lambda_function" "llm_interaction_lambda" {
  function_name = "c22-dv-llm-interaction-service"
  role          = aws_iam_role.iam_for_llm_lambda.arn # Updated reference
  package_type  = "Image"
  architectures = ["x86_64"]
  image_uri     = "${aws_ecr_repository.llm-interaction-repo.repository_url}:latest"
  timeout       = 60 
  memory_size   = 512

  environment {
    variables = {
      SECRET_ID = aws_secretsmanager_secret.credentials.name
    }
  }
}

resource "aws_lambda_function_url" "llm_endpoint" {
  function_name      = aws_lambda_function.llm_interaction_lambda.function_name
  authorization_type = "NONE"

  cors {
    allow_origins  = ["*"]
    allow_methods  = ["POST", "GET"]
    allow_headers  = ["content-type"]
    expose_headers = ["keep-alive", "date"]
    max_age        = 86400
  }
}

resource "aws_iam_role_policy" "llm_lambda_logging_and_secrets" {
  name = "llm-lambda-base-permissions"
  role = aws_iam_role.iam_for_llm_lambda.id # Updated reference

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        # Pattern-based ARN avoids "ResourceAlreadyExists" errors
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/c22-dv-llm-interaction-service:*"
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.credentials.arn 
      },
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = "*" 
      }
    ]
  })
}

output "lambda_url" {
  description = "The HTTP URL endpoint for the LLM Lambda"
  value       = aws_lambda_function_url.llm_endpoint.function_url
}