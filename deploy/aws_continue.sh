#!/bin/bash

# Trump Trader - Continue AWS Deployment (after version fix)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() { echo -e "${BLUE}==>${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }

REGION="ap-northeast-1"
PROJECT_NAME="trump-trader"

# Use existing resources
RDS_SG_ID="sg-03d64bc5859fc9a46"
PUBLIC_SUBNET_ID="subnet-01f6f90cffcb12805"
PRIVATE_SUBNET_ID="subnet-02815fa6590c757fd"
EC2_SG_ID="sg-05df4a314eb076fc9"

echo "================================================================================"
echo "🚀 Continuing AWS Deployment - Creating RDS & EC2"
echo "================================================================================"
echo ""

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 24)

# Create RDS instance with correct version
print_step "Creating RDS PostgreSQL 15.8 instance (5-10 minutes)..."
aws rds create-db-instance \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --engine-version 15.8 \
    --master-username trump_trader \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 20 \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name ${PROJECT_NAME}-db-subnet \
    --backup-retention-period 7 \
    --no-publicly-accessible \
    --db-name trump_trader \
    --region $REGION \
    --tags "Key=Name,Value=$PROJECT_NAME-db" >/dev/null

print_success "RDS instance creation started"
print_step "Waiting for database (5-10 minutes)..."

aws rds wait db-instance-available \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --region $REGION

DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --region $REGION \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

print_success "Database ready: $DB_ENDPOINT"

echo ""
echo "================================================================================"
echo "PHASE 4: EC2 INSTANCE"
echo "================================================================================"
echo ""

# Create key pair (skip if exists)
print_step "Creating SSH key pair..."
if [ ! -f "${PROJECT_NAME}-key.pem" ]; then
    aws ec2 create-key-pair \
        --key-name ${PROJECT_NAME}-key \
        --region $REGION \
        --query 'KeyMaterial' \
        --output text > ${PROJECT_NAME}-key.pem
    chmod 400 ${PROJECT_NAME}-key.pem
    print_success "SSH key saved: ${PROJECT_NAME}-key.pem"
else
    print_success "SSH key already exists"
fi

# Get latest Ubuntu 22.04 AMI
print_step "Finding latest Ubuntu 22.04 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --region $REGION \
    --output text)
print_success "AMI: $AMI_ID"

# Launch EC2 instance
print_step "Launching EC2 instance (t3.small)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t3.small \
    --key-name ${PROJECT_NAME}-key \
    --security-group-ids $EC2_SG_ID \
    --subnet-id $PUBLIC_SUBNET_ID \
    --associate-public-ip-address \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT_NAME-bot}]" \
    --region $REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

print_success "EC2 instance launched: $INSTANCE_ID"
print_step "Waiting for instance..."

aws ec2 wait instance-running \
    --instance-ids $INSTANCE_ID \
    --region $REGION

EC2_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

print_success "Instance ready: $EC2_IP"

echo ""
echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""
echo "💾 Database:     $DB_ENDPOINT"
echo "🖥️  EC2:          $EC2_IP"
echo "🔑 SSH Key:      ${PROJECT_NAME}-key.pem"
echo ""
echo "================================================================================"
echo "📝 SAVE THIS INFORMATION:"
echo "================================================================================"
echo ""
echo "DATABASE_URL=postgresql://trump_trader:$DB_PASSWORD@$DB_ENDPOINT:5432/trump_trader"
echo ""
echo "================================================================================"
echo "🚀 NEXT STEPS:"
echo "================================================================================"
echo ""
echo "1. Wait 2-3 minutes for EC2 initialization"
echo ""
echo "2. Connect to EC2:"
echo "   ssh -i ${PROJECT_NAME}-key.pem ubuntu@$EC2_IP"
echo ""
echo "3. On EC2, clone and deploy:"
echo "   git clone https://github.com/Mmmauz1001/trump_trader.git"
echo "   cd trump_trader"
echo "   nano .env  # Add your API keys and DATABASE_URL"
echo "   ./deploy/deploy.sh"
echo ""
echo "================================================================================"

# Save configuration
cat > ${PROJECT_NAME}-aws-config.txt << CONFIG
AWS Deployment Configuration
Generated: $(date)

Region: $REGION
Database: $DB_ENDPOINT
Database Password: $DB_PASSWORD
DATABASE_URL: postgresql://trump_trader:$DB_PASSWORD@$DB_ENDPOINT:5432/trump_trader

EC2 Instance: $INSTANCE_ID
EC2 IP: $EC2_IP
SSH Key: ${PROJECT_NAME}-key.pem

Connect: ssh -i ${PROJECT_NAME}-key.pem ubuntu@$EC2_IP

Security Groups:
- EC2: $EC2_SG_ID
- RDS: $RDS_SG_ID

Subnets:
- Public: $PUBLIC_SUBNET_ID
- Private: $PRIVATE_SUBNET_ID
CONFIG

print_success "Configuration saved: ${PROJECT_NAME}-aws-config.txt"
echo ""

