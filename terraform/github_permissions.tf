# --- 1. GitHub OIDC Identity Provider ---
# This allows GitHub to talk to AWS without passwords/keys
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["1c5815a4a15c156637373f73c683777d85c4909a"] 
}

# --- 2. IAM Role for GitHub Actions ---
resource "aws_iam_role" "github_actions_ecr" {
  name = "github-actions-ecr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Condition = {
          StringLike = {
            # CRITICAL: Restrict this to ONLY your specific repository
            "token.actions.githubusercontent.com:sub" = "repo:ConnorCalkin/DisinformationVerifier:*"
          }
        }
      }
    ]
  })
}

# --- 3. Permissions Policy ---
# Added 'ecr:CreateRepository' and 'ecr:DescribeRepositories' 
# so the GitHub workflow can auto-create missing repos.
resource "aws_iam_role_policy" "ecr_policy" {
  name = "github-actions-ecr-policy"
  role = aws_iam_role.github_actions_ecr.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:CreateRepository"
        ]
        Resource = "*"
      }
    ]
  })
}

# --- 4. ECR Repositories ---
locals {
  repo_names = [
    "c22-dv-wiki-ner-repo",
    "c22-dv-url-scraper-repo",
    "c22-dv-rag-image",
    "c22-dv-pipeline-image",
    "c22-dv-streamlit-image"
  ]
}

resource "aws_ecr_repository" "repos" {
  for_each             = toset(local.repo_names)
  name                 = each.value
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- 5. Lifecycle Policy (Cost Savings) ---
# Automatically deletes old images, keeping only the 10 most recent.
resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each   = toset(local.repo_names)
  repository = aws_ecr_repository.repos[each.value].name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images to save costs"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# --- Outputs ---
output "role_arn" {
  value       = aws_iam_role.github_actions_ecr.arn
  description = "Copy this ARN into your GitHub Action 'role-to-assume' field."
}