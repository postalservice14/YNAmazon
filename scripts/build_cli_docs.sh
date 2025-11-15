#!/bin/bash

# This script generates documentation for the CLI using Typer's utils.

# Ensure the script exits on error
set -e

# Path to the CLI file
CLI_FILE="ynamazon.cli.cli"

# Output directory for the generated documentation
OUTPUT_FILENAME="CLI_README.md"
CLI_NAME="yna"

# Set dummy environment variables for documentation generation
# (Settings validation requires these to be present)
export YNAB_API_KEY="dummy_key_for_docs"
export YNAB_BUDGET_ID="dummy_budget_id_for_docs"
export AMAZON_USER="dummy@example.com"
export AMAZON_PASSWORD="dummy_password_for_docs"

# Generate the documentation using Typer's utils
uv run python -m typer "$CLI_FILE" utils docs --output "$OUTPUT_FILENAME" --name "$CLI_NAME"

echo "Documentation generated successfully as '$OUTPUT_FILENAME'."
