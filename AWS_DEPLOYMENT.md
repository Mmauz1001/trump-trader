# AWS Deployment Guide - Trump Trader Bot

Complete guide to deploy the Trump Trader bot to AWS in Tokyo region (`ap-northeast-1`).

## 📋 Prerequisites

- AWS Account
- AWS CLI installed and configured
- SSH key pair for EC2 access
- Domain name (optional, for HTTPS)

## 💰 Estimated Monthly Cost

- **EC2 (t3.small)**: ~$15/month
- **RDS PostgreSQL (db.t4g.micro)**: ~$15-20/month
- **Data Transfer**: ~$1-2/month
- **Total**: **~$30-35/month**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Tokyo Region                        │
│                    (ap-northeast-1)                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                        VPC                           │  │
│  │                    10.0.0.0/16                       │  │
│  │                                                      │  │
│  │  ┌────────────────────┐  ┌─────────────────────┐   │  │
│  │  │   Public Subnet    │  │   Private Subnet    │   │  │
│  │  │   10.0.1.0/24      │  │   10.0.2.0/24       │   │  │
│  │  │                    │  │                     │   │  │
│  │  │  ┌──────────────┐  │  │  ┌──────────────┐  │   │  │
│  │  │  │   EC2        │  │  │  │     RDS      │  │   │  │
│  │  │  │  t3.small    │  │  │  │  PostgreSQL  │  │   │  │
│  │  │  │              │  │  │  │              │  │   │  │
│  │  │  │  - main.py   │◄─┼──┼─►│  Database    │  │   │  │
│  │  │  │  - telegram  │  │  │  │              │  │   │  │
│  │  │  │              │  │  │  └──────────────┘  │   │  │
│  │  │  └──────────────┘  │  │                     │   │  │
│  │  │         ▲          │  │                     │   │  │
│  │  └─────────┼──────────┘  └─────────────────────┘   │  │
│  │            │                                        │  │
│  └────────────┼────────────────────────────────────────┘  │
│               │                                           │
└───────────────┼───────────────────────────────────────────┘
                │
                ▼
        ┌───────────────┐
        │   Internet    │
        │   Gateway     │
        └───────────────┘
                │
        ┌───────┴────────┐
        │                │
    Twitter API     Binance API
    Claude API      Telegram API
```

---

## 🚀 Deployment Steps

### Phase 1: AWS Infrastructure Setup (30-45 minutes)

#### 1.1 Create VPC

```bash
# Create VPC
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --region ap-northeast-1 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=trump-trader-vpc}]'

# Note the VPC ID from the output
export VPC_ID=vpc-xxxxx
```

#### 1.2 Create Subnets

```bash
# Create public subnet
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone ap-northeast-1a \
    --region ap-northeast-1 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=trump-trader-public}]'

export PUBLIC_SUBNET_ID=subnet-xxxxx

# Create private subnet
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone ap-northeast-1a \
    --region ap-northeast-1 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=trump-trader-private}]'

export PRIVATE_SUBNET_ID=subnet-xxxxx
```

#### 1.3 Create Internet Gateway

```bash
# Create and attach Internet Gateway
aws ec2 create-internet-gateway \
    --region ap-northeast-1 \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=trump-trader-igw}]'

export IGW_ID=igw-xxxxx

aws ec2 attach-internet-gateway \
    --vpc-id $VPC_ID \
    --internet-gateway-id $IGW_ID \
    --region ap-northeast-1
```

#### 1.4 Configure Route Table

```bash
# Get main route table
aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --region ap-northeast-1

export ROUTE_TABLE_ID=rtb-xxxxx

# Add route to Internet Gateway
aws ec2 create-route \
    --route-table-id $ROUTE_TABLE_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID \
    --region ap-northeast-1
```

#### 1.5 Create Security Groups

```bash
# EC2 Security Group
aws ec2 create-security-group \
    --group-name trump-trader-ec2-sg \
    --description "Security group for Trump Trader EC2" \
    --vpc-id $VPC_ID \
    --region ap-northeast-1

export EC2_SG_ID=sg-xxxxx

# Allow SSH
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region ap-northeast-1

# Allow HTTPS (optional, for future web dashboard)
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region ap-northeast-1

# RDS Security Group
aws ec2 create-security-group \
    --group-name trump-trader-rds-sg \
    --description "Security group for Trump Trader RDS" \
    --vpc-id $VPC_ID \
    --region ap-northeast-1

export RDS_SG_ID=sg-xxxxx

# Allow PostgreSQL from EC2 SG
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID \
    --region ap-northeast-1
```

#### 1.6 Create RDS PostgreSQL

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name trump-trader-db-subnet \
    --db-subnet-group-description "Subnet group for Trump Trader DB" \
    --subnet-ids $PRIVATE_SUBNET_ID $PUBLIC_SUBNET_ID \
    --region ap-northeast-1

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier trump-trader-db \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username trump_trader \
    --master-user-password 'YOUR_SECURE_PASSWORD' \
    --allocated-storage 20 \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name trump-trader-db-subnet \
    --backup-retention-period 7 \
    --no-publicly-accessible \
    --region ap-northeast-1

# Wait for DB to be available (takes 5-10 minutes)
aws rds wait db-instance-available \
    --db-instance-identifier trump-trader-db \
    --region ap-northeast-1

# Get DB endpoint
aws rds describe-db-instances \
    --db-instance-identifier trump-trader-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --region ap-northeast-1
```

#### 1.7 Launch EC2 Instance

```bash
# Create key pair
aws ec2 create-key-pair \
    --key-name trump-trader-key \
    --region ap-northeast-1 \
    --query 'KeyMaterial' \
    --output text > trump-trader-key.pem

chmod 400 trump-trader-key.pem

# Launch EC2 instance (Ubuntu 22.04)
aws ec2 run-instances \
    --image-id ami-0d52744d6551d851e \
    --instance-type t3.small \
    --key-name trump-trader-key \
    --security-group-ids $EC2_SG_ID \
    --subnet-id $PUBLIC_SUBNET_ID \
    --associate-public-ip-address \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=trump-trader-bot}]' \
    --region ap-northeast-1

# Get instance public IP
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=trump-trader-bot" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --region ap-northeast-1
```

---

### Phase 2: Application Deployment (30 minutes)

#### 2.1 Connect to EC2

```bash
export EC2_IP=your-ec2-public-ip
ssh -i trump-trader-key.pem ubuntu@$EC2_IP
```

#### 2.2 Deploy Application

```bash
# On EC2 instance
curl -O https://raw.githubusercontent.com/Mmmauz1001/trump_trader/main/deploy/deploy.sh
chmod +x deploy.sh

# Edit .env file with your configuration
nano /home/ubuntu/trump_trader/.env

# Update DATABASE_URL with RDS endpoint:
# DATABASE_URL=postgresql://trump_trader:YOUR_PASSWORD@your-rds-endpoint.ap-northeast-1.rds.amazonaws.com:5432/trump_trader

# Run deployment
./deploy.sh
```

---

### Phase 3: Verification (15 minutes)

#### 3.1 Check Services

```bash
# Check main bot
sudo systemctl status trump-trader.service

# Check telegram handler
sudo systemctl status trump-trader-telegram.service

# View logs
sudo journalctl -u trump-trader.service -f
```

#### 3.2 Verify in Telegram

You should receive a startup notification in your Telegram channel showing:
- ✅ Status: Online
- Account balance
- System information

---

## 🔧 Management Commands

### View Logs
```bash
# Main bot logs
sudo journalctl -u trump-trader.service -f

# Telegram handler logs
sudo journalctl -u trump-trader-telegram.service -f

# Both logs together
sudo journalctl -u trump-trader.service -u trump-trader-telegram.service -f
```

### Restart Services
```bash
# Restart main bot
sudo systemctl restart trump-trader.service

# Restart telegram handler
sudo systemctl restart trump-trader-telegram.service

# Restart both
sudo systemctl restart trump-trader.service trump-trader-telegram.service
```

### Update Application
```bash
cd /home/ubuntu/trump_trader
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart trump-trader.service trump-trader-telegram.service
```

---

## 📊 Monitoring Setup (Optional)

### CloudWatch Logs

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure to send logs to CloudWatch
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/home/ubuntu/trump_trader/deploy/cloudwatch-config.json
```

---

## 🔒 Security Best Practices

1. **Use AWS Secrets Manager** for API keys (not .env)
2. **Enable CloudWatch alarms** for system failures
3. **Set up automatic backups** for RDS
4. **Use IAM roles** instead of access keys where possible
5. **Enable MFA** on AWS account
6. **Restrict SSH access** to your IP only
7. **Keep system updated**: `sudo apt update && sudo apt upgrade`

---

## 🆘 Troubleshooting

### Database Connection Issues
```bash
# Test DB connection from EC2
psql -h your-rds-endpoint.ap-northeast-1.rds.amazonaws.com \
     -U trump_trader \
     -d trump_trader
```

### Service Won't Start
```bash
# Check detailed error logs
sudo journalctl -u trump-trader.service -n 100 --no-pager

# Check Python errors
python /home/ubuntu/trump_trader/main.py start
```

### Out of Memory
```bash
# Check memory usage
free -h

# Add swap space if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📱 Support

For issues or questions:
- Check logs: `sudo journalctl -u trump-trader.service -f`
- Telegram: Monitor your Trump Trader channel for error alerts
- GitHub: https://github.com/Mmmauz1001/trump_trader

---

## ✅ Deployment Checklist

- [ ] VPC and subnets created
- [ ] Security groups configured
- [ ] RDS PostgreSQL running
- [ ] EC2 instance launched
- [ ] Application deployed
- [ ] Services running
- [ ] Telegram notifications working
- [ ] Twitter monitoring active
- [ ] First trade executed successfully
- [ ] Monitoring and alerts set up
- [ ] Backups configured

**Total Time**: 2-3 hours
**Monthly Cost**: ~$30-35

---

🎉 **You're now running a professional 24/7 automated trading bot on AWS!**

