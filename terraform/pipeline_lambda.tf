data "aws_ecr_repository" "pipeline_repo" {
    name = "c22-dv-pipeline-image"
}

data "aws_ecr_image" "pipeline_image" {
    repository_name = data.aws_ecr_repository.pipeline_repo.name
    image_tag = "latest"
}

resource "aws_lambda_function" "pipeline_lambda" {
    function_name = "c22-dv-pipeline-lambda"
    role          = aws_iam_role.rds_connect_lambda_role.arn

    package_type = "Image"
    image_uri    = "${data.aws_ecr_repository.pipeline_repo.repository_url}@${data.aws_ecr_image.pipeline_image.id}"

    timeout      = 60
    memory_size  = 512

    environment {
        variables = {
            RDS_HOST     = aws_db_instance.rds_instance.address
            RDS_PORT     = 5432
            RDS_DB       = var.db_name
            RDS_USER     = var.db_username
            RDS_PASSWORD = random_password.master.result
            SECRET_ID    = aws_secretsmanager_secret.credentials.name
        }
    }
}