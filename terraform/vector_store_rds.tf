data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.credentials.id
}

resource "aws_security_group" "rds_sg" {
  name   = "c22-dv-postgres-sg"
  vpc_id = var.vpc_id 

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] 
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "c22-dv-main-subnet-group"
  subnet_ids = var.subnet_ids 

}

resource "aws_db_instance" "rds_instance" {
  identifier             = "c22-dv-vector-store" 
  allocated_storage      = 10
  db_name                = var.db_name
  engine                 = "postgres"
  engine_version         = "13"
  instance_class         = "db.t3.micro"
  username               = var.db_username
  password               = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["RDS_PASSWORD"]
  parameter_group_name   = "default.postgres13"
  skip_final_snapshot    = true
  
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  
  publicly_accessible    = true 
}