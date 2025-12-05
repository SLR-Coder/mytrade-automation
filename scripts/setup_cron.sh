#!/bin/bash
# MyTrade Automation - Cron Setup Script
# Run this script to set up automated scheduling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  MyTrade Automation - Cron Setup"
echo "=========================================="

# Create log directory
LOG_DIR="/var/log/mytrade"
echo "Creating log directory: $LOG_DIR"
sudo mkdir -p "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"

# Create log files
for log in robot1 robot2 robot6 robot9 pipeline weekly; do
    sudo touch "$LOG_DIR/$log.log"
    sudo chmod 644 "$LOG_DIR/$log.log"
done

echo "Log directory created successfully"

# Update crontab paths
echo "Updating crontab with project path: $PROJECT_DIR"
sed "s|/home/user/mytrade-automation|$PROJECT_DIR|g" "$SCRIPT_DIR/crontab.txt" > /tmp/mytrade_crontab.txt

# Show the crontab
echo ""
echo "Crontab configuration:"
echo "=========================================="
cat /tmp/mytrade_crontab.txt
echo "=========================================="

# Ask for confirmation
echo ""
read -p "Install this crontab? (y/n): " confirm

if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    crontab /tmp/mytrade_crontab.txt
    echo ""
    echo "Crontab installed successfully!"
    echo ""
    echo "View current crontab: crontab -l"
    echo "Edit crontab: crontab -e"
    echo "Remove crontab: crontab -r"
    echo ""
    echo "Logs will be written to: $LOG_DIR"
    echo ""
    echo "To monitor logs in real-time:"
    echo "  tail -f $LOG_DIR/pipeline.log"
else
    echo "Crontab installation cancelled"
fi

# Cleanup
rm -f /tmp/mytrade_crontab.txt

echo ""
echo "Setup complete!"
