#!/bin/bash
# LEGO Price Analysis Pipeline
# Runs: eBay scraper -> price analysis -> email report
# Triggered automatically by launchd every 2 weeks.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$PROJECT_DIR/pipeline.log"

# Redirect all output to log file (also keep stdout for manual runs)
exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo "======================================================"
echo " LEGO Price Pipeline started: $(date)"
echo "======================================================"

# Use the conda env's python directly — avoids conda activate issues in launchd
PYTHON="/opt/anaconda3/envs/ebayfetchsold/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: Python not found at $PYTHON"
    echo "Check that the conda environment 'ebayfetchsold' exists."
    exit 1
fi

echo "Using Python: $PYTHON"
cd "$PROJECT_DIR"

# --- Step 1: Fetch market data from eBay ---
echo ""
echo "[1/3] Fetching market data from eBay..."
if ! "$PYTHON" src/get_market_data.py; then
    echo "ERROR: get_market_data.py failed. Aborting pipeline."
    exit 1
fi

# --- Step 2: Run price comparison analysis ---
echo ""
echo "[2/3] Running price analysis..."
if ! "$PYTHON" src/price_comparison.py; then
    echo "ERROR: price_comparison.py failed. Aborting pipeline."
    exit 1
fi

# --- Step 3: Send email report ---
echo ""
echo "[3/3] Sending email report..."
if ! "$PYTHON" src/email_report.py; then
    echo "ERROR: email_report.py failed. Check config.json and Gmail App Password."
    exit 1
fi

echo ""
echo "======================================================"
echo " Pipeline completed: $(date)"
echo "======================================================"
