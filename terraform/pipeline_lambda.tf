data "aws_ecr_repository" "pipeline_repo" {
    name = "c22-dv-pipeline-image"
}

resource "aws_lambda_function" "pipeline_lambda" {
    function_name = "c22-dv-pipeline-lambda"
    role          = aws_iam_role.rds_connect_lambda_role.arn

    package_type = "Image"
    image_uri    = "${data.aws_ecr_repository.pipeline_repo.repository_url}:latest"

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