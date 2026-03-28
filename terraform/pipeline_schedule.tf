resource "aws_iam_role" "scheduler_role" {
    name = "c22-dv-scheduler-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Action = "sts:AssumeRole",
                Effect = "Allow",
                Principal = {
                    Service = "scheduler.amazonaws.com"
                }
            }
        ]
    })
}

resource "aws_iam_policy" "scheduler_lambda_invoke_policy" {
    name = "c22-dv-scheduler-lambda-invoke-policy"
    
    policy = jsonencode({
        Version = "2012-10-17",
        Statement = [{
            Effect   = "Allow",
            Action   = ["lambda:InvokeFunction"],
            Resource = aws_lambda_function.pipeline_lambda.arn
        }]
    })
}

resource "aws_iam_role_policy_attachment" "scheduler_lambda_invoke" {
    role       = aws_iam_role.scheduler_role.name
    policy_arn = aws_iam_policy.scheduler_lambda_invoke_policy.arn
}

#create schedule group
resource "aws_scheduler_schedule_group" "pipeline_schedule_group" {
  name = "c22-dv-schedule-group"
}


resource "aws_scheduler_schedule" "pipeline_schedule" {
  name       = "c22-dv-pipeline-schedule"
  group_name = aws_scheduler_schedule_group.pipeline_schedule_group.name

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(30 minutes)"

  target {
    arn      = aws_lambda_function.pipeline_lambda.arn
    role_arn = aws_iam_role.scheduler_role.arn
  }
}

