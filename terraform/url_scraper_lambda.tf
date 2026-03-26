resource "aws_lambda_function" "url_scraper_lambda" {
    function_name = "c22-dv-url-scraper-lambda"
    role          = aws_iam_role.lambda_role.arn

    package_type = "Image"
    image_uri    = "${aws_ecr_repository.url_scraper_repo.repository_url}@${data.aws_ecr_image.url_scraper_lambda_image.id}"

    timeout      = 60
    memory_size  = 512
}

resource "aws_lambda_permission" "allow_lambda_url" {
  statement_id           = "AllowFunctionUrlInvocation"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.url_scraper_lambda.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function_url" "scraper_url" {
  function_name      = aws_lambda_function.url_scraper_lambda.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST"]
    allow_headers     = ["date", "keep-alive", "content-type"]
    max_age           = 86400
  }
}

resource "aws_cloudwatch_log_group" "scraper_logs" {
  name              = "/aws/lambda/${aws_lambda_function.url_scraper_lambda.function_name}"
  retention_in_days = 7
}

# Output the URL so you can find it easily after running terraform apply
output "function_url" {
  value = aws_lambda_function_url.scraper_url.function_url
}