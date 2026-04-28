#!/usr/bin/env bash
# Stops webhook server + ngrok
echo "Stopping webhook + ngrok..."
pkill -f "python.*webhook_server.py" 2>/dev/null || true
pkill -f "ngrok http 3020"           2>/dev/null || true
rm -f .webhook.pid .ngrok.pid
echo "Stopped."
