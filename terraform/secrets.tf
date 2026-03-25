resource "aws_secretsmanager_secret" "credentials" {
    name = "c22-dv-credentials"
    description = "API key for OpenAI access used by the Disinformation Verifier application"
}

resource "aws_secretsmanager_secret_version" "credentials_val" {
    secret_id     = aws_secretsmanager_secret.credentials.id
    secret_string = jsonencode({
        "OPENAI_API_KEY" = "placeholder-for-openai-api-key-value",
        "RDS_PASSWORD" = "placeholder"
    })

    lifecycle {
        ignore_changes = [secret_string] # Prevent Terraform from trying to update the secret value on every apply
    }
}