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

# --- Activate conda ---
CONDA_FOUND=false
for conda_base in "$HOME/miniconda3" "$HOME/miniforge3" "$HOME/anaconda3" \
                  "/opt/homebrew/Caskroom/miniconda/base" \
                  "/opt/anaconda3" "/opt/miniconda3"; do
    if [ -f "$conda_base/etc/profile.d/conda.sh" ]; then
        source "$conda_base/etc/profile.d/conda.sh"
        conda activate ebayfetchsold
        echo "Conda activated from: $conda_base"
        CONDA_FOUND=true
        break
    fi
done

if [ "$CONDA_FOUND" = false ]; then
    echo "ERROR: Could not find conda. Tried common install paths."
    echo "Please add the correct conda path to run_pipeline.sh"
    exit 1
fi

cd "$PROJECT_DIR"

# --- Step 1: Fetch market data from eBay ---
echo ""
echo "[1/3] Fetching market data from eBay..."
if ! python src/get_market_data.py; then
    echo "ERROR: get_market_data.py failed. Aborting pipeline."
    exit 1
fi

# --- Step 2: Run price comparison analysis ---
echo ""
echo "[2/3] Running price analysis..."
if ! python src/price_comparison.py; then
    echo "ERROR: price_comparison.py failed. Aborting pipeline."
    exit 1
fi

# --- Step 3: Send email report ---
echo ""
echo "[3/3] Sending email report..."
if ! python src/email_report.py; then
    echo "ERROR: email_report.py failed. Check config.json and Gmail App Password."
    exit 1
fi

echo ""
echo "======================================================"
echo " Pipeline completed: $(date)"
echo "======================================================"
