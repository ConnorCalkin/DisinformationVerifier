import boto3

TABLE_NAME = "user_responses"


def add_response(dynamodb_client, user_id: str, published_date: str) -> None:
    """
    Adds an article to the DynamoDB table.
    """
    dynamodb_client.put_item(
        TableName=TABLE_NAME,
        Item={
            "user_id": {"S": user_id},
            "published_at": {"S": published_date}
        }
    )


def get_responses(dynamodb_client, user_id: str) -> list[dict]:
    """
    Retrieves the articles for a given user from the DynamoDB table.
    """
    response = dynamodb_client.query(
        TableName=TABLE_NAME,
        KeyConditionExpression="user_id = :user_id",
        ExpressionAttributeValues={":user_id": {"S": user_id}}
    )
    items = response.get("Items", [])
    return items


def delete_response(dynamodb_client, user_id: str, published_date: str) -> None:
    """
    Deletes a specific article from the DynamoDB table.
    """
    dynamodb_client.delete_item(
        TableName=TABLE_NAME,
        Key={
            "user_id": {"S": user_id},
            "published_at": {"S": published_date}
        }
    )


if __name__ == "__main__":
    dynamodb_client = boto3.client("dynamodb")
    # Example usage
    add_response(dynamodb_client, "user123", "2024-06-01T12:00:00Z")
    responses = get_responses(dynamodb_client, "user123")
    print(responses)
    delete_response(dynamodb_client, "user123", "2024-06-01T12:00:00Z")
