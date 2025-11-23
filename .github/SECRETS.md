# GitHub Actions Secrets Setup

Add these secrets to your GitHub repository:
Settings → Secrets and variables → Actions → New repository secret

## Required Secrets

### SSH_PRIVATE_KEY
Your SSH private key for deployment
```
-----BEGIN OPENSSH PRIVATE KEY-----
... (copy from C:\Users\pieti\.ssh\id_ed25519)
-----END OPENSSH PRIVATE KEY-----
```

### SSH_USER
```
your-ssh-username
```

### SERVER_HOST
```
your-server-ip
```

### DATABASE_URL
```
postgresql://user:YOUR_DB_PASSWORD@localhost:5432/pp2stats
```
Note: Uses `localhost` because container runs with `--network host`

### CORS_ORIGINS
```
http://localhost:3000,http://YOUR_SERVER_IP,https://your-frontend-domain.com
```

## Testing Deployment

After pushing to main branch:
1. Go to Actions tab in GitHub
2. Watch the workflow run
3. Check deployment: http://YOUR_SERVER_IP:8000/docs
