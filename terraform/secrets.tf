resource "aws_secretsmanager_secret" "openai_key" {
    name = "c22-dv-openai-api-key"
    description = "API key for OpenAI access used by the Disinformation Verifier application"
}

resource "aws_secretsmanager_secret_version" "openai_key_val" {
    secret_id     = aws_secretsmanager_secret.openai_key.id
    secret_string = jsonencode({
        "OPENAI_API_KEY" = "placeholder-for-openai-api-key-value"
    })

    lifecycle {
        ignore_changes = [secret_string] # Prevent Terraform from trying to update the secret value on every apply
    }
}