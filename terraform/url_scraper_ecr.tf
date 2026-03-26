resource "aws_ecr_repository" "url_scraper_repo" {
    name = "c22-dv-url-scraper-repo"
    image_tag_mutability = "MUTABLE"
    force_delete = true

    image_scanning_configuration {
      scan_on_push = true
    }
}

data "aws_ecr_image" "url_scraper_lambda_image" {
    repository_name = aws_ecr_repository.url_scraper_repo.name
    image_tag = "latest"
}