variable "db_username" {
  description = "Username for the RDS database"
  type        = string
  default = "postgres"
}

variable "db_password" {
  description = "Password for the RDS database"
  type = string
  sensitive = true
}

variable "db_name" {
  description = "Name of the RDS database"
  type        = string
  default = "vector_db"
}

variable "vpc_id" {
  description = "The ID of the VPC where the RDS instance will be deployed"
  type        = string
  default = "vpc-03f0d39570fbaa750"
}

variable "subnet_ids" {
  description = "A list of subnet IDs for the RDS subnet group"
  type        = list(string)
  default = [ "subnet-046ec8b4e41d59ea8", "subnet-0cfeaca0e941dea5b" ]
}