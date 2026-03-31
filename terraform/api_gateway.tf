resource "aws_apigatewayv2_api" "main" {
  name          = "c22-dv-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
    max_age       = 86400
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# --- RAG ---

resource "aws_apigatewayv2_integration" "rag" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.rag_lambda.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "rag" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /rag"
  target    = "integrations/${aws_apigatewayv2_integration.rag.id}"
}

resource "aws_lambda_permission" "apigw_rag" {
  statement_id  = "AllowAPIGatewayInvokeRag"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rag_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# --- Wiki NER ---

resource "aws_apigatewayv2_integration" "wiki" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.wiki_ner_lambda.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "wiki" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /wiki"
  target    = "integrations/${aws_apigatewayv2_integration.wiki.id}"
}

resource "aws_lambda_permission" "apigw_wiki" {
  statement_id  = "AllowAPIGatewayInvokeWiki"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.wiki_ner_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# --- URL Scraper ---

resource "aws_apigatewayv2_integration" "scraper" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.url_scraper_lambda.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "scraper" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /scrape"
  target    = "integrations/${aws_apigatewayv2_integration.scraper.id}"
}

resource "aws_lambda_permission" "apigw_scraper" {
  statement_id  = "AllowAPIGatewayInvokeScraper"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.url_scraper_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

output "api_gateway_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}