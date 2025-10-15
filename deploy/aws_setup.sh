#!/bin/bash

# Trump Trader - AWS Infrastructure Setup Script
# Region: ap-northeast-1 (Tokyo)

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REGION="ap-northeast-1"
PROJECT_NAME="trump-trader"

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

echo "================================================================================"
echo "🚀 AWS Infrastructure Setup - Trump Trader Bot"
echo "================================================================================"
echo ""
echo "Region: $REGION (Tokyo)"
echo "Account: $(aws sts get-caller-identity --query Account --output text)"
echo ""
print_warning "This will create AWS resources that incur costs (~\$30/month)"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "================================================================================"
echo "PHASE 1: VPC & NETWORKING"
echo "================================================================================"
echo ""

# Step 1: Create VPC
print_step "Creating VPC..."
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --region $REGION \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT_NAME-vpc}]" \
    --query 'Vpc.VpcId' \
    --output text)
print_success "VPC created: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-hostnames \
    --region $REGION

# Step 2: Create Subnets
print_step "Creating public subnet..."
PUBLIC_SUBNET_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone ${REGION}a \
    --region $REGION \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public}]" \
    --query 'Subnet.SubnetId' \
    --output text)
print_success "Public subnet created: $PUBLIC_SUBNET_ID"

print_step "Creating private subnet..."
PRIVATE_SUBNET_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone ${REGION}c \
    --region $REGION \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private}]" \
    --query 'Subnet.SubnetId' \
    --output text)
print_success "Private subnet created: $PRIVATE_SUBNET_ID"

# Step 3: Create and attach Internet Gateway
print_step "Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
    --region $REGION \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-igw}]" \
    --query 'InternetGateway.InternetGatewayId' \
    --output text)

aws ec2 attach-internet-gateway \
    --vpc-id $VPC_ID \
    --internet-gateway-id $IGW_ID \
    --region $REGION
print_success "Internet Gateway created and attached: $IGW_ID"

# Step 4: Configure Route Table
print_step "Configuring route table..."
ROUTE_TABLE_ID=$(aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --region $REGION \
    --query 'RouteTables[0].RouteTableId' \
    --output text)

aws ec2 create-route \
    --route-table-id $ROUTE_TABLE_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID \
    --region $REGION >/dev/null 2>&1 || true
print_success "Route table configured: $ROUTE_TABLE_ID"

echo ""
echo "================================================================================"
echo "PHASE 2: SECURITY GROUPS"
echo "================================================================================"
echo ""

# Step 5: Create EC2 Security Group
print_step "Creating EC2 security group..."
EC2_SG_ID=$(aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-ec2-sg \
    --description "Security group for Trump Trader EC2" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' \
    --output text)

# Get your public IP
MY_IP=$(curl -s https://checkip.amazonaws.com)

# Allow SSH from your IP only
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr ${MY_IP}/32 \
    --region $REGION
print_success "EC2 Security Group created: $EC2_SG_ID (SSH allowed from $MY_IP)"

# Step 6: Create RDS Security Group
print_step "Creating RDS security group..."
RDS_SG_ID=$(aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-rds-sg \
    --description "Security group for Trump Trader RDS" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' \
    --output text)

# Allow PostgreSQL from EC2 SG
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID \
    --region $REGION
print_success "RDS Security Group created: $RDS_SG_ID"

echo ""
echo "================================================================================"
echo "PHASE 3: DATABASE (RDS PostgreSQL)"
echo "================================================================================"
echo ""

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 24)

# Create DB subnet group
print_step "Creating DB subnet group..."
aws rds create-db-subnet-group \
    --db-subnet-group-name ${PROJECT_NAME}-db-subnet \
    --db-subnet-group-description "Subnet group for Trump Trader DB" \
    --subnet-ids $PUBLIC_SUBNET_ID $PRIVATE_SUBNET_ID \
    --region $REGION \
    --tags "Key=Name,Value=$PROJECT_NAME-db-subnet" >/dev/null
print_success "DB subnet group created"

# Create RDS instance
print_step "Creating RDS PostgreSQL instance (this takes 5-10 minutes)..."
aws rds create-db-instance \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --engine-version 15.4 \
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
print_step "Waiting for database to be available (5-10 minutes)..."

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

# Create key pair
print_step "Creating SSH key pair..."
aws ec2 create-key-pair \
    --key-name ${PROJECT_NAME}-key \
    --region $REGION \
    --query 'KeyMaterial' \
    --output text > ${PROJECT_NAME}-key.pem

chmod 400 ${PROJECT_NAME}-key.pem
print_success "SSH key saved: ${PROJECT_NAME}-key.pem"

# Get latest Ubuntu 22.04 AMI
print_step "Finding latest Ubuntu 22.04 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*" \
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
print_step "Waiting for instance to be running..."

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
echo "✅ INFRASTRUCTURE SETUP COMPLETE!"
echo "================================================================================"
echo ""
echo "📋 DEPLOYMENT SUMMARY:"
echo "────────────────────────────────────────────────────────────────────────────"
echo ""
echo "🌐 VPC:              $VPC_ID"
echo "🔒 EC2 Security Grp: $EC2_SG_ID"
echo "🔒 RDS Security Grp: $RDS_SG_ID"
echo "💾 Database:         $DB_ENDPOINT"
echo "🖥️  EC2 Instance:     $EC2_IP"
echo "🔑 SSH Key:          ${PROJECT_NAME}-key.pem"
echo ""
echo "================================================================================"
echo "📝 SAVE THIS INFORMATION:"
echo "================================================================================"
echo ""
echo "DATABASE_URL=postgresql://trump_trader:$DB_PASSWORD@$DB_ENDPOINT:5432/trump_trader"
echo ""
echo "Save this connection string - you'll need it for the .env file!"
echo ""
echo "================================================================================"
echo "🚀 NEXT STEPS:"
echo "================================================================================"
echo ""
echo "1. Wait 2-3 minutes for EC2 to finish initializing"
echo ""
echo "2. Connect to EC2:"
echo "   ssh -i ${PROJECT_NAME}-key.pem ubuntu@$EC2_IP"
echo ""
echo "3. Deploy application:"
echo "   Run the deployment commands from AWS_DEPLOYMENT.md Phase 2"
echo ""
echo "4. Update .env with DATABASE_URL shown above"
echo ""
echo "================================================================================"
echo ""

# Save configuration
cat > ${PROJECT_NAME}-aws-config.txt << CONFIG
AWS Infrastructure Configuration
Generated: $(date)

Region: $REGION
VPC ID: $VPC_ID
Public Subnet: $PUBLIC_SUBNET_ID
Private Subnet: $PRIVATE_SUBNET_ID
EC2 Security Group: $EC2_SG_ID
RDS Security Group: $RDS_SG_ID
Internet Gateway: $IGW_ID
Route Table: $ROUTE_TABLE_ID

Database Endpoint: $DB_ENDPOINT
Database Password: $DB_PASSWORD
DATABASE_URL: postgresql://trump_trader:$DB_PASSWORD@$DB_ENDPOINT:5432/trump_trader

EC2 Instance: $INSTANCE_ID
EC2 Public IP: $EC2_IP
SSH Key: ${PROJECT_NAME}-key.pem

SSH Command:
ssh -i ${PROJECT_NAME}-key.pem ubuntu@$EC2_IP
CONFIG

print_success "Configuration saved to: ${PROJECT_NAME}-aws-config.txt"
echo ""
print_warning "🔐 IMPORTANT: Keep the config file secure - it contains sensitive credentials!"
echo ""

