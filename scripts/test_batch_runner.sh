#!/usr/bin/env bash
set -euo pipefail

RUNS=20
FAILURES=0
LOG_DIR=$(mktemp -d)

echo "Failure logs will be written to: $LOG_DIR"
echo ""

for i in $(seq 1 $RUNS); do
    echo -n "Run $i/$RUNS ..."
    LOG_FILE="$LOG_DIR/run_$(printf '%02d' "$i").log"
    if poetry run ./manage.py test --settings=cms.settings.test --parallel auto --shuffle 2>&1 | tee "$LOG_FILE"; then
        echo "OK"
        rm "$LOG_FILE"
    else
        echo "FAILED - logged to $LOG_FILE"
        ((FAILURES++))
    fi
done

echo ""
echo "Result: $FAILURES/$RUNS runs failed"
if [ $FAILURES -gt 0 ]; then
    echo "Check the logs in $LOG_DIR for details."
fi
