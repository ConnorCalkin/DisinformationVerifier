
resource "aws_ecr_repository" "llm-interaction-repo" {
    name = "c22-dv-llm-interaction-repo"
    image_tag_mutability = "MUTABLE"
    force_delete = true

    image_scanning_configuration {
      scan_on_push = true
    }
}

data "aws_ecr_image" "llm_interaction_image" {
    repository_name = aws_ecr_repository.llm-interaction-repo.name
    image_tag = "latest"
}


# The Execution Role
resource "aws_iam_role" "iam_for_lambda" {
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

# Logging & Secrets Permissions
resource "aws_iam_role_policy" "lambda_logging_and_secrets" {
  name = "lambda-base-permissions"
  role = aws_iam_role.iam_for_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        # Secure this by replacing "*" with your specific Secret ARN if possible
        Resource = aws_secretsmanager_secret.credentials.arn 
      }
    ]
  })
}

resource "aws_lambda_function" "llm_interaction_lambda" {
  function_name = "c22-dv-llm-interaction-service"
  role          = aws_iam_role.iam_for_lambda.arn
  package_type  = "Image"
  architectures = ["arm64"]

  # Points to the image you pushed to your ECR
  image_uri = "${aws_ecr_repository.llm-interaction-repo.repository_url}:latest"

  # No vpc_config block needed! Default networking is active.

  # LLM calls are often slow; 60s is a safe starting point
  timeout     = 60 
  memory_size = 512

  environment {
        variables = {
            SECRET_ID = aws_secretsmanager_secret.credentials.name
        }

  }
}

resource "aws_lambda_function_url" "llm_endpoint" {
  function_name      = aws_lambda_function.llm_interaction_lambda.function_name
  authorization_type = "NONE" # Change to "AWS_IAM" later for production security

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["POST", "GET"]
    allow_headers     = ["content-type"]
    expose_headers    = ["keep-alive", "date"]
    max_age           = 86400
  }
}

output "lambda_url" {
  description = "The HTTP URL endpoint for the LLM Lambda"
  value       = aws_lambda_function_url.llm_endpoint.function_url
}