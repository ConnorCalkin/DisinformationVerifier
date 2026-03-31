data "aws_ecr_repository" "streamlit_repo" {
    name = "c22-dv-streamlit-image"
}

data "aws_ecr_image" "streamlit_image" {
    repository_name = data.aws_ecr_repository.streamlit_repo.name
    image_tag = "latest"
}

resource "aws_ecs_cluster" "dashboard_cluster" {
    name = "c22-dv-dashboard-cluster"
}

resource "aws_iam_role" "ecs_task_execution_role" {
    name = "c22-dv-ecs-task-execution-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Action = "sts:AssumeRole",
                Effect = "Allow",
                Principal = {
                    Service = "ecs-tasks.amazonaws.com"
                }
            }
        ]
    })
}

resource "aws_iam_role" "ecs_task_role" {
    name = "c22-dv-ecs-task-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Action = "sts:AssumeRole",
                Effect = "Allow",
                Principal = {
                    Service = "ecs-tasks.amazonaws.com"
                }
            }
        ]
    })
}

resource "aws_iam_policy" "ecs_task_lambda_invoke_policy" {
    name = "c22-dv-ecs-task-lambda-invoke-policy"

    policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Effect = "Allow",
                Action = [
                    "lambda:InvokeFunctionUrl"
                ],
                Resource = [aws_lambda_function.rag_lambda.arn,
                aws_lambda_function.wiki_ner_lambda.arn] 

            }
        ]
    })
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_lambda_invoke" {
    role       = aws_iam_role.ecs_task_role.name
    policy_arn = aws_iam_policy.ecs_task_lambda_invoke_policy.arn
  
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_rds_access" {
    role       = aws_iam_role.ecs_task_role.name
    policy_arn = aws_iam_policy.rds_connect_rds_access_policy.arn
}

resource "aws_iam_policy" "ecs_execution_secrets_policy" {
    name        = "c22-dv-ecs-execution-secrets-policy"
    description = "Allows ECS Agent to pull secrets for env vars"

    policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Effect = "Allow",
                Action = [
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:ListSecrets"
                ],
                Resource = [
                    aws_secretsmanager_secret.credentials.arn,
                ]
            }
        ]
    })
}
 
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_secrets_read" {
    role       = aws_iam_role.ecs_task_execution_role.name
    policy_arn = aws_iam_policy.ecs_execution_secrets_policy.arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_secrets_read" {
    role       = aws_iam_role.ecs_task_role.name
    policy_arn = aws_iam_policy.ecs_execution_secrets_policy.arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_basic_execution" {
    role       = aws_iam_role.ecs_task_execution_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_cloudwatch_logs" {
    role       = aws_iam_role.ecs_task_execution_role.name
    policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_cloudwatch_log_group" "ecs_log_group" {
  name              = "/ecs/c22-dv-dashboard"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "dashboard_task" {
    family                   = "c22-dv-dashboard-task"
    network_mode             = "awsvpc"
    requires_compatibilities = ["FARGATE"]
    cpu                      = "512"
    memory                   = "1024"
    execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
    task_role_arn            = aws_iam_role.ecs_task_role.arn

    container_definitions    = jsonencode([
        {
            name      = "dashboard-container",
            image     = "${data.aws_ecr_repository.streamlit_repo.repository_url}@${data.aws_ecr_image.streamlit_image.id}",
            essential = true,
            portMappings = [
                {
                    containerPort = 8501,
                    hostPort      = 8501,
                    protocol      = "tcp"
                }
            ]
            environment = [
                { name = "RAG_URL", value = aws_lambda_function_url.rag_lambda_url.function_url },
                { name = "WIKI_URL", value = aws_lambda_function_url.wiki_ner_lambda_url.function_url },
                { name = "SCRAPE_URL", value = aws_lambda_function_url.scraper_url.function_url },
                { name = "RDS_HOST",       value = aws_db_instance.rds_instance.address },
                { name = "RDS_PORT",       value = "5432" },
                { name = "RDS_DB",         value = "user_history" },
                { name = "RDS_USER",       value = var.db_username },
                { name = "SECRET_ID",      value = aws_secretsmanager_secret.credentials.name },
                { name = "AWS_REGION",     value = "eu-west-2" },
                { name = "RDS_PASSWORD",   value = random_password.master.result }
            ],
            logConfiguration = {
                logDriver = "awslogs",
                options = {
                    "awslogs-group"         = aws_cloudwatch_log_group.ecs_log_group.name,
                    "awslogs-region"        = "eu-west-2",
                    "awslogs-stream-prefix" = "ecs"
                }
            }
        }
    ])
    lifecycle {
      ignore_changes = [container_definitions]
    }
}

resource "aws_security_group" "ecs_sg" {
    name   = "c22-dv-ecs-sg"
    vpc_id = var.vpc_id 

    ingress {
        from_port   = 8501
        to_port     = 8501
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}

resource "aws_ecs_service" "dashboard_service" {
    name            = "c22-dv-dashboard-service"
    cluster         = aws_ecs_cluster.dashboard_cluster.id
    task_definition = aws_ecs_task_definition.dashboard_task.arn
    desired_count   = 1
    launch_type     = "FARGATE"

    network_configuration {
        subnets         = var.subnet_ids
        security_groups = [aws_security_group.ecs_sg.id]
        assign_public_ip = true
    }

    lifecycle {
    ignore_changes = [
      desired_count,   # Let Auto Scaling handle the scaling
      task_definition, # If you use 'aws ecs update-service' in CI/CD
    ]
  }
}
    
