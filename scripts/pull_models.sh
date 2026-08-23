#!/usr/bin/env bash
# Sovereign AI Workbench — Model Pull Script (TRD §13, §29.1)
# Pulls the three configured open-weight models into local Ollama storage.
set -euo pipefail

echo "============================================================"
echo "Sovereign AI Workbench: Pulling Local Open-Weight Models"
echo "============================================================"

MODELS=(
    "qwen2.5:7b-instruct-q4_K_M"
    "qwen2.5-coder:7b-instruct-q4_K_M"
    "llava:7b-q4_K_M"
)

for model in "${MODELS[@]}"; do
    echo "Pulling local model: ${model}..."
    ollama pull "${model}" || {
        echo "Error: Failed to pull ${model}. Ensure Ollama daemon is running."
        exit 1
    }
done

echo "All local open-weight models pulled successfully."
