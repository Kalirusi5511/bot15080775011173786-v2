#!/bin/bash

echo "==================================="
echo "🚀 Render Start"
echo "==================================="

echo "🤖 Starte Discord Bot..."

python app.py &
BOT_PID=$!

echo "🤖 Discord Bot PID: $BOT_PID"

echo "🌐 Starte Gunicorn..."

gunicorn \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 1 \
    --threads 2 \
    --timeout 120 \
    app:app &

GUNICORN_PID=$!

echo "🌐 Gunicorn PID: $GUNICORN_PID"

CLEANED_UP=false

cleanup() {

    if [ "$CLEANED_UP" = true ]; then
        return
    fi

    CLEANED_UP=true

    echo ""
    echo "==================================="
    echo "🛑 Render beendet den Service"
    echo "==================================="

    echo "🛑 Stoppe Discord Bot..."
    kill -TERM "$BOT_PID" 2>/dev/null || true

    echo "🛑 Stoppe Gunicorn..."
    kill -TERM "$GUNICORN_PID" 2>/dev/null || true

    wait "$BOT_PID" 2>/dev/null || true
    wait "$GUNICORN_PID" 2>/dev/null || true

    echo "✅ Prozesse beendet."
}

trap cleanup SIGTERM SIGINT

wait -n "$BOT_PID" "$GUNICORN_PID"

EXIT_CODE=$?

echo "⚠️ Ein Hauptprozess wurde beendet."
echo "⚠️ Exit Code: $EXIT_CODE"

cleanup

exit "$EXIT_CODE"
