# EC2 Deployment Guide

This deployment layout runs the app on one EC2 instance behind `nginx`:

- React frontend served by `nginx`
- FastAPI agent API on `127.0.0.1:8000`
- Express auth API on `127.0.0.1:800`

`nginx` serves the frontend and reverse-proxies:

- `/api/*` -> FastAPI
- `/auth/*` -> Express auth

Because the frontend now defaults to same-origin production paths, the app can
be deployed on one hostname without rebuilding for every environment.

## Recommended directories

- App repo: `/opt/virtual-economist`
- Frontend build output served by nginx: `/var/www/virtual-economist/current`
- Env files: `/etc/virtual-economist/`

## 1. Install system packages

Amazon Linux 2023 example:

```bash
sudo dnf update -y
sudo dnf install -y nginx nodejs npm python3.11 python3.11-pip git rsync
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If `uv` installs into `~/.local/bin`, make sure that path is available to the
deployment user and in the systemd service `PATH`.

Your screenshots show:

- OS: Amazon Linux 2023
- User path assumption: `ec2-user`
- Public IP: `13.223.95.253`
- Public DNS: `ec2-13-223-95-253.compute-1.amazonaws.com`

The included `systemd` service files already target that shape.

## 2. Clone the repo

```bash
sudo mkdir -p /opt/virtual-economist
sudo chown "$USER":"$USER" /opt/virtual-economist
git clone <your-repo-url> /opt/virtual-economist
cd /opt/virtual-economist
```

## 3. Create env files

Create these files:

- `/etc/virtual-economist/fastapi.env`
- `/etc/virtual-economist/auth.env`

Use the examples in:

- `infra/ec2/env/fastapi.env.example`
- `infra/ec2/env/auth.env.example`

## 4. Install app dependencies

```bash
cd /opt/virtual-economist
uv --project backend sync
cd backend && npm ci
cd ../frontend && npm ci && npm run build
sudo mkdir -p /var/www/virtual-economist/current
sudo rsync -av --delete build/ /var/www/virtual-economist/current/
```

## 5. Install systemd services

Copy and edit the service files if your EC2 username or app path differs from
the defaults.

```bash
sudo cp infra/ec2/systemd/virtual-economist-fastapi.service /etc/systemd/system/
sudo cp infra/ec2/systemd/virtual-economist-auth.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable virtual-economist-fastapi
sudo systemctl enable virtual-economist-auth
sudo systemctl start virtual-economist-fastapi
sudo systemctl start virtual-economist-auth
```

## 6. Install nginx config

```bash
sudo cp infra/ec2/nginx/virtual-economist.conf /etc/nginx/sites-available/virtual-economist
sudo ln -sf /etc/nginx/sites-available/virtual-economist /etc/nginx/sites-enabled/virtual-economist
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Health checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:800/health
curl http://YOUR_EC2_HOSTNAME/
curl http://YOUR_EC2_HOSTNAME/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is Apple current stock price?"}'
```

## 8. Rolling updates

Run:

```bash
cd /opt/virtual-economist
bash infra/ec2/scripts/deploy.sh
```

## Security group reminder

Open these inbound ports on the instance security group:

- `80` for HTTP
- `443` for HTTPS once TLS is configured

Do not expose `8000` or `800` publicly if nginx is the public entrypoint.

## TLS

Once the app is up on port `80`, install TLS with Certbot:

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

## Troubleshooting

Check service logs:

```bash
sudo journalctl -u virtual-economist-fastapi -f
sudo journalctl -u virtual-economist-auth -f
sudo nginx -t
```
