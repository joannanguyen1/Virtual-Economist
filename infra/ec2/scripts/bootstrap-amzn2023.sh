#!/usr/bin/env bash
set -euo pipefail

sudo dnf update -y
sudo dnf install -y \
  git \
  nginx \
  nodejs \
  npm \
  python3.11 \
  python3.11-pip \
  rsync \
  tar

curl -LsSf https://astral.sh/uv/install.sh | sh

sudo mkdir -p /opt/virtual-economist
sudo chown ec2-user:ec2-user /opt/virtual-economist
sudo mkdir -p /var/www/virtual-economist/current
sudo mkdir -p /etc/virtual-economist

echo "Bootstrap complete."
echo "Next steps:"
echo "1. Clone the repo to /opt/virtual-economist"
echo "2. Copy env files into /etc/virtual-economist/"
echo "3. Run infra/ec2/scripts/deploy.sh"
echo "4. Install the systemd and nginx configs from infra/ec2/"
