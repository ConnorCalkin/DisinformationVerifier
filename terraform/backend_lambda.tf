resource "aws_ecr_repository" "backend-repo" {
  name                 = "c22-dv-backend-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# The Execution Role - Unique identifier
resource "aws_iam_role" "backend_lambda_role" {
  name = "c22-dv-backend-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" } 
    }]
  })
}

resource "aws_lambda_function" "backend_lambda" {
  function_name = "c22-dv-backend-service"
  role          = aws_iam_role.backend_lambda_role.arn # Updated reference
  package_type  = "Image"
  architectures = ["x86_64"]
  image_uri     = "${aws_ecr_repository.backend-repo.repository_url}:latest"
  timeout       = 60 
  memory_size   = 512

  environment {
    variables = {
      SECRET_ID  = aws_secretsmanager_secret.credentials.name
      RAG_URL    = aws_lambda_function_url.rag_lambda_url.function_url
      WIKI_URL   = aws_lambda_function_url.wiki_ner_lambda_url.function_url
      SCRAPE_URL = aws_lambda_function_url.scraper_url.function_url
      LLM_URL    = aws_lambda_function_url.llm_endpoint.function_url
    }
  }
}

resource "aws_lambda_function_url" "backend_endpoint" {
  function_name      = aws_lambda_function.backend_lambda.function_name
  authorization_type = "NONE" 

  cors {
    allow_origins  = ["*"]
    allow_methods  = ["POST", "GET"]
    allow_headers  = ["content-type"]
    expose_headers = ["keep-alive", "date"]
    max_age        = 86400
  }
}

resource "aws_iam_role_policy" "lambda_backend_permissions" {
  name = "c22-dv-backend-permissions"
  role = aws_iam_role.backend_lambda_role.id # Updated reference

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
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/c22-dv-backend-service:*" 
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.credentials.arn 
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunctionUrl",
          "lambda:InvokeFunction"
        ]
        Resource = "*" 
      }
    ]
  })
}

output "backend_url" {
  description = "The HTTP URL endpoint for the Backend Lambda"
  value       = aws_lambda_function_url.backend_endpoint.function_url 
}