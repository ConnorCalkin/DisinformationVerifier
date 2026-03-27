data "aws_ecr_repository" "rag_repo" {
  name = "c22-dv-rag-image"
}

data "aws_ecr_image" "rag_image" {
    repository_name = data.aws_ecr_repository.rag_repo.name
    image_tag = "latest"
}

data "aws_secretsmanager_secret_version" "credentials_val" {
    secret_id = aws_secretsmanager_secret.credentials.id
}

resource "aws_lambda_function_url" "rag_lambda_url" {
  function_name      = aws_lambda_function.rag_lambda.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "allow_public_access_rag_lambda" {
  statement_id           = "AllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.rag_lambda.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function" "rag_lambda" {
    function_name = "c22-dv-rag-lambda"
    role          = aws_iam_role.rds_connect_lambda_role.arn

    package_type = "Image"
    image_uri    = "${data.aws_ecr_repository.rag_repo.repository_url}@${data.aws_ecr_image.rag_image.id}"

    timeout      = 60
    memory_size  = 512

    environment {
        variables = {
            RDS_HOST     = aws_db_instance.rds_instance.address
            RDS_PORT     = 5432
            RDS_DB       = var.db_name
            RDS_USER     = var.db_username
            RDS_PASSWORD = jsondecode(data.aws_secretsmanager_secret_version.credentials_val.secret_string)["RDS_PASSWORD"]
            SECRET_ID    = aws_secretsmanager_secret.credentials.name
        }
    }
}