#!/usr/bin/env bash
# ============================================================
# WhatsApp Claude Agent — Linux/macOS starter
# ============================================================

set -e

if [ ! -f "config.py" ]; then
    echo "ERROR: config.py not found. Run ./install.sh first."
    exit 1
fi

echo ""
echo "=== WhatsApp Claude Agent - Start ==="
echo ""

# --- Kill old processes ---
echo "[1/3] Cleaning old processes..."
pkill -f "python.*webhook_server.py" 2>/dev/null || true
pkill -f "ngrok http 3020"           2>/dev/null || true
sleep 1

# --- Start webhook server ---
echo "[2/3] Starting webhook server on :3020..."
nohup python3 webhook_server.py > webhook.log 2> webhook.err.log &
echo $! > .webhook.pid
sleep 2

# --- Start ngrok ---
echo "[3/3] Starting ngrok tunnel..."
nohup ngrok http 3020 > ngrok.log 2>&1 &
echo $! > .ngrok.pid
sleep 3

# --- Fetch ngrok URL ---
PUBLIC_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null || echo "")

echo ""
echo "=== READY ==="
echo ""
if [ -n "$PUBLIC_URL" ]; then
    echo "Webhook URL (paste into megaAPI):"
    echo "  $PUBLIC_URL/?session=1"
else
    echo "WARNING: Could not fetch ngrok URL. Check: http://127.0.0.1:4040"
fi
echo ""
echo "For session 2, 3, ...: append ?session=N"
echo ""
echo "Next: in Claude Code session, set Monitor to:"
echo "  python3 monitor.py 1"
echo ""
echo "Logs: webhook.log / webhook.err.log / ngrok.log"
echo "Stop: ./stop.sh"
