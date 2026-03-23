terraform {
  # Requires Terraform 1.10 or higher for native S3 locking
  required_version = ">= 1.10.0"

  backend "s3" {
    bucket         = "c22-dv-terraform-state-bucket"
    key            = "dev/terraform.tfstate" # Where in the bucket to store the file
    region         = "eu-west-2"
    encrypt        = true
    
    use_lockfile   = true 
  }
}