# GitHub Actions CI/CD Setup

Automatic deployment to AWS EC2 when you push to the `main` branch.

## 🚀 How It Works

Every time you push to `main`, GitHub Actions will:
1. ✅ Pull latest code on EC2
2. ✅ Install dependencies
3. ✅ Restart both services
4. ✅ Verify services are running

**Total deployment time: ~30 seconds**

---

## 🔐 Required GitHub Secrets

You need to add these secrets to your GitHub repository:

### **1. Go to GitHub Repository Settings**

https://github.com/Mmmauz1001/trump_trader/settings/secrets/actions

Or navigate:
- Go to your repository
- Click **Settings**
- Click **Secrets and variables** → **Actions**
- Click **New repository secret**

### **2. Add These Secrets:**

#### **Secret 1: `EC2_HOST`**
- **Name**: `EC2_HOST`
- **Value**: `18.181.203.148`

#### **Secret 2: `EC2_SSH_KEY`**
- **Name**: `EC2_SSH_KEY`
- **Value**: Copy the contents of `trump-trader-key.pem`

To get the key contents:
```bash
cat trump-trader-key.pem
```

Copy everything including:
```
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
```

---

## ✅ Testing the Pipeline

### **Method 1: Push to Main**
```bash
git add .
git commit -m "Deploy to AWS"
git push origin main
```

### **Method 2: Manual Trigger**
1. Go to: https://github.com/Mmmauz1001/trump_trader/actions
2. Click **Deploy to AWS EC2**
3. Click **Run workflow** → **Run workflow**

---

## 📊 Monitoring Deployments

### **View Deployment Status:**
https://github.com/Mmmauz1001/trump_trader/actions

You'll see:
- ✅ Green checkmark = Deployment successful
- ❌ Red X = Deployment failed
- 🟡 Yellow dot = Deployment in progress

### **View Deployment Logs:**
1. Click on any workflow run
2. Click on the **Deploy to Production** job
3. See detailed logs of each step

---

## 🛡️ Safety Features

- **Automatic rollback**: If deployment fails, old code keeps running
- **Service verification**: Checks that services started successfully
- **Manual trigger**: Can deploy without pushing code
- **Branch protection**: Only deploys from `main` branch

---

## 🔧 Customization

### **Deploy to Different Branch:**

Edit `.github/workflows/deploy.yml`:
```yaml
on:
  push:
    branches:
      - main
      - production  # Add more branches
```

### **Add Slack/Discord Notifications:**

Add notification step to workflow (can be added later)

### **Add Tests Before Deploy:**

Add test job before deployment (recommended for production)

---

## 📋 One-Time EC2 Setup (Already Done!)

These were completed during initial deployment:
- ✅ Services installed
- ✅ Git repository cloned
- ✅ `.env` file configured
- ✅ Services running

---

## 🎯 Workflow Triggers

The pipeline runs when:
1. **Push to main**: Automatic deployment
2. **Manual trigger**: From GitHub Actions UI
3. **Pull request merged**: When PR is merged to main

---

## ⚡ Quick Start Checklist

- [ ] Add `EC2_HOST` secret to GitHub
- [ ] Add `EC2_SSH_KEY` secret to GitHub
- [ ] Push this file to trigger first deployment
- [ ] Check Actions tab for deployment status
- [ ] Verify bot is running via Telegram

---

## 🆘 Troubleshooting

### **Deployment fails with "Permission denied"**
- Check that `EC2_SSH_KEY` secret contains the full private key
- Verify key includes header/footer lines

### **Services fail to restart**
- SSH into EC2 and check logs:
  ```bash
  sudo journalctl -u trump-trader.service -f
  ```

### **"Host key verification failed"**
- The EC2 IP might have changed
- Update `EC2_HOST` secret with new IP

---

## 🎉 Benefits

✅ **No manual SSH needed** - Just push code  
✅ **Consistent deployments** - Same process every time  
✅ **Fast** - Deploys in ~30 seconds  
✅ **Visible** - See deployment status in GitHub  
✅ **Safe** - Services only restart if code pulls successfully  

---

**After setting up secrets, every push to `main` will automatically deploy to AWS!** 🚀

