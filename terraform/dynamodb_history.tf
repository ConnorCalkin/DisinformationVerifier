#create dynamodb table to store article history
resource "aws_dynamodb_table" "article_history" {
    name           = "article_history"
    billing_mode   = "PAY_PER_REQUEST"
    hash_key       = "user_id"
    range_key      = "published_at"

    attribute {
        name = "user_id"
        type = "S"
    }

    attribute {
        name = "published_at"
        type = "S"
    }
}