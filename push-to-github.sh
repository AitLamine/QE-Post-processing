#!/bin/bash
# Push QE Post-processing Lab to GitHub. Run this from a terminal where you're
# already authenticated to GitHub (SSH key added, or `gh auth login`, or you'll
# be prompted for a username + personal access token on the push step).
#
# Usage:
#   cd ~/Desktop/New-Stuff/CrystalEdu-App/dft-postprocessing
#   bash push-to-github.sh

set -e

# 1. Point this repo at your GitHub repo (skip if you already added it).
git remote add origin https://github.com/AitLamine/QE-Post-processing.git 2>/dev/null \
  || git remote set-url origin https://github.com/AitLamine/QE-Post-processing.git

# 2. Push main and set it to track origin, so future `git push` just works.
git push -u origin main

echo "Done. Repo live at: https://github.com/AitLamine/QE-Post-processing"
