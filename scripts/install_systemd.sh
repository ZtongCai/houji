#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$project_dir" != "/home/houjiagent/houji" ]]; then
  echo "Expected project at /home/houjiagent/houji, got: $project_dir" >&2
  exit 2
fi

sudo install -m 0644 "$project_dir/deploy/systemd/houji-brain.service" /etc/systemd/system/houji-brain.service
sudo install -m 0644 "$project_dir/deploy/systemd/houji-dashboard.service" /etc/systemd/system/houji-dashboard.service
sudo install -m 0644 "$project_dir/deploy/systemd/houji.target" /etc/systemd/system/houji.target
sudo install -m 0644 "$project_dir/deploy/systemd/houji-cpolar.service" /etc/systemd/system/houji-cpolar.service
sudo systemctl daemon-reload
sudo systemctl enable --now houji.target
sudo systemctl --no-pager --full status houji-brain.service houji-dashboard.service houji-cpolar.service
