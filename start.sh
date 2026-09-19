#!/bin/bash

echo "==================================="
echo "🚀 Render Start"
echo "==================================="

python app.py &

BOT_PID=$!

echo "🤖 Discord Bot PID: $BOT_PID"
echo "🌐 Starte Gunicorn auf Port $PORT"

exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 2 \
    --timeout 120 \
    app:app
