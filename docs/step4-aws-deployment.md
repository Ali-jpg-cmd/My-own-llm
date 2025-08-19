# Step 4: AWS Deployment

## Overview

This guide covers deploying your AI API to AWS using EC2, ECS, or Lambda. We'll provide multiple deployment options with cost estimates and best practices.

## Deployment Options

### Option 1: EC2 Instance (Recommended for LLM)

**Best for:** Running local models like LLaMA 3
**Cost:** $50-500/month depending on instance size
**Complexity:** Medium

### Option 2: ECS with Fargate

**Best for:** Containerized deployment without server management
**Cost:** $30-200/month
**Complexity:** Low

### Option 3: Lambda + API Gateway

**Best for:** Serverless with hosted models (OpenAI, Anthropic)
**Cost:** $5-50/month
**Complexity:** Low

## Option 1: EC2 Deployment

### Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
```

### Step 1: Create Security Group

```bash
# Create security group
aws ec2 create-security-group \
    --group-name llm-api-sg \
    --description "Security group for LLM API"

# Add rules
aws ec2 authorize-security-group-ingress \
    --group-name llm-api-sg \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name llm-api-sg \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name llm-api-sg \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name llm-api-sg \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0
```

### Step 2: Launch EC2 Instance

```bash
# Launch GPU instance (g4dn.xlarge for LLaMA 3)
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type g4dn.xlarge \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --iam-instance-profile Name=llm-api-role \
    --user-data file://user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=llm-api-server}]'
```

### Step 3: User Data Script

Create `user-data.sh`:

```bash
#!/bin/bash
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone https://github.com/your-repo/my-own-llm.git /opt/llm-api
cd /opt/llm-api

# Create environment file
cat > .env << EOF
DATABASE_URL=postgresql://llm_user:llm_password@localhost/llm_api
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET=your-jwt-secret-change-in-production
LLM_PROVIDER=huggingface
LLM_MODEL=meta-llama/Llama-2-7b-chat-hf
DEBUG=false
EOF

# Start services
docker-compose up -d
```

### Step 4: Install NVIDIA Drivers (for GPU instances)

```bash
# SSH into instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install NVIDIA drivers
sudo yum install -y kernel-devel-$(uname -r)
wget https://us.download.nvidia.com/XFree86/Linux-x86_64/470.82.01/NVIDIA-Linux-x86_64-470.82.01.run
sudo sh NVIDIA-Linux-x86_64-470.82.01.run --silent

# Install Docker NVIDIA runtime
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

## Option 2: ECS with Fargate

### Step 1: Create ECR Repository

```bash
# Create repository
aws ecr create-repository --repository-name llm-api

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

# Build and push image
docker build -t llm-api .
docker tag llm-api:latest your-account.dkr.ecr.us-east-1.amazonaws.com/llm-api:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/llm-api:latest
```

### Step 2: Create Task Definition

Create `task-definition.json`:

```json
{
    "family": "llm-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "2048",
    "memory": "4096",
    "executionRoleArn": "arn:aws:iam::your-account:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "llm-api",
            "image": "your-account.dkr.ecr.us-east-1.amazonaws.com/llm-api:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "DATABASE_URL",
                    "value": "postgresql://user:pass@your-rds-endpoint/db"
                },
                {
                    "name": "REDIS_URL",
                    "value": "redis://your-elasticache-endpoint:6379"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/llm-api",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
```

### Step 3: Create ECS Service

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
    --cluster your-cluster \
    --service-name llm-api \
    --task-definition llm-api:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Option 3: Lambda + API Gateway

### Step 1: Create Lambda Function

Create `lambda_function.py`:

```python
import json
import os
from app.main import app
from mangum import Mangum

# Create handler for Lambda
handler = Mangum(app)

def lambda_handler(event, context):
    return handler(event, context)
```

### Step 2: Deploy with Serverless Framework

Create `serverless.yml`:

```yaml
service: llm-api

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  environment:
    DATABASE_URL: ${ssm:/llm-api/database-url}
    REDIS_URL: ${ssm:/llm-api/redis-url}
    SECRET_KEY: ${ssm:/llm-api/secret-key}
    JWT_SECRET: ${ssm:/llm-api/jwt-secret}

functions:
  api:
    handler: lambda_function.lambda_handler
    events:
      - http:
          path: /{proxy+}
          method: ANY
    memorySize: 1024
    timeout: 30

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
    layer:
      name: python-deps
      description: Python dependencies for LLM API
```

### Step 3: Deploy

```bash
# Install Serverless Framework
npm install -g serverless

# Deploy
serverless deploy
```

## Terraform Deployment

### Complete Infrastructure as Code

Create `main.tf`:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "llm-api-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  
  tags = {
    Name = "llm-api-public-subnet"
  }
}

# Security Group
resource "aws_security_group" "llm_api" {
  name        = "llm-api-sg"
  description = "Security group for LLM API"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
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

# EC2 Instance
resource "aws_instance" "llm_api" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "g4dn.xlarge"
  
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.llm_api.id]
  associate_public_ip_address = true
  
  key_name = "your-key-pair"
  
  user_data = file("user-data.sh")
  
  tags = {
    Name = "llm-api-server"
  }
}

# RDS Database
resource "aws_db_instance" "llm_api" {
  identifier = "llm-api-db"
  
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  
  db_name  = "llm_api"
  username = "llm_user"
  password = "llm_password"
  
  vpc_security_group_ids = [aws_security_group.llm_api.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  
  tags = {
    Name = "llm-api-database"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "llm_api" {
  cluster_id           = "llm-api-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  security_group_ids = [aws_security_group.llm_api.id]
  subnet_group_name  = aws_elasticache_subnet_group.main.name
}

# Outputs
output "instance_public_ip" {
  value = aws_instance.llm_api.public_ip
}

output "database_endpoint" {
  value = aws_db_instance.llm_api.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.llm_api.cache_nodes.0.address
}
```

### Deploy with Terraform

```bash
# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply
```

## Cost Estimates

### EC2 (g4dn.xlarge)
- **Instance:** $0.526/hour = ~$380/month
- **Storage:** $0.10/GB = ~$10/month
- **Data Transfer:** $0.09/GB = ~$20/month
- **Total:** ~$410/month

### ECS Fargate
- **CPU/Memory:** $0.04048/vCPU-hour + $0.004445/GB-hour = ~$100/month
- **Load Balancer:** $16/month
- **Total:** ~$116/month

### Lambda + API Gateway
- **Lambda:** $0.20 per 1M requests = ~$10/month
- **API Gateway:** $3.50 per 1M requests = ~$20/month
- **Total:** ~$30/month

## Monitoring and Logging

### CloudWatch Setup

```bash
# Create log group
aws logs create-log-group --log-group-name /aws/llm-api

# Create dashboard
aws cloudwatch put-dashboard \
    --dashboard-name "LLM-API-Metrics" \
    --dashboard-body file://dashboard.json
```

### Dashboard Configuration

Create `dashboard.json`:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApiGateway", "Count", "ApiName", "llm-api"],
          [".", "Latency", ".", "."],
          [".", "4XXError", ".", "."],
          [".", "5XXError", ".", "."]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "API Gateway Metrics"
      }
    }
  ]
}
```

## SSL/TLS Setup

### Using AWS Certificate Manager

```bash
# Request certificate
aws acm request-certificate \
    --domain-name api.yourdomain.com \
    --validation-method DNS

# Create Application Load Balancer
aws elbv2 create-load-balancer \
    --name llm-api-alb \
    --subnets subnet-xxx subnet-yyy \
    --security-groups sg-xxx \
    --scheme internet-facing \
    --type application
```

## Backup and Recovery

### Database Backup

```bash
# Create automated backup
aws rds create-db-snapshot \
    --db-instance-identifier llm-api-db \
    --db-snapshot-identifier llm-api-backup-$(date +%Y%m%d)
```

### Application Backup

```bash
# Create AMI
aws ec2 create-image \
    --instance-id i-xxxxxxxxx \
    --name "llm-api-backup-$(date +%Y%m%d)" \
    --description "LLM API backup"
```

## Next Steps

1. **Choose deployment option** based on your needs
2. **Set up monitoring** with CloudWatch
3. **Configure SSL** for production
4. **Set up backups** for data protection
5. **Test thoroughly** before going live
