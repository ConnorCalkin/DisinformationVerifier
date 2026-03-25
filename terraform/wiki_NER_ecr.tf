resource "aws_ecr_repository" "wiki_ner_repo" {
    name = "c22-dv-wiki-ner-repo"
    image_tag_mutability = "MUTABLE"
    force_delete = true

    image_scanning_configuration {
      scan_on_push = true
    }
}

data "aws_ecr_image" "wiki_ner_lambda_image" {
    repository_name = aws_ecr_repository.wiki_ner_repo.name
    image_tag = "latest"
}