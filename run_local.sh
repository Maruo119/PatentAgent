#!/bin/bash

# Local execution script for PatentAgent Lambda handler
# Usage: ./run_local.sh

echo "============================================"
echo "PatentAgent - Local Execution Script"
echo "============================================"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo ""
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo ""
    echo "Then edit .env with your credentials:"
    echo "  - JPO_API_ID"
    echo "  - JPO_API_PASSWORD"
    echo "  - SLACK_WEBHOOK_URL"
    exit 1
fi

echo "✓ .env file found"
echo ""

# Check if requirements are installed
echo "Checking dependencies..."
packages=("requests" "python-dotenv" "boto3")
missing=()

for package in "${packages[@]}"; do
    python3 -c "import ${package//-/_}" 2>/dev/null
    if [ $? -ne 0 ]; then
        missing+=("$package")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing packages: ${missing[@]}"
    echo ""
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

echo "✓ All dependencies installed"
echo ""

# Run the handler
echo "Executing Lambda handler..."
echo "============================================"
echo ""

python3 -c "
import sys
import os
import json

# Add src/lambda to path
sys.path.insert(0, 'src/lambda')
os.chdir('src/lambda')

# Load environment variables
from dotenv import load_dotenv
load_dotenv('../../.env')

# Import and run handler
try:
    from handler import lambda_handler
    result = lambda_handler({}, None)

    # Parse and display result
    if isinstance(result, dict):
        status_code = result.get('statusCode', 'N/A')
        body = result.get('body', '{}')

        print(f'Status Code: {status_code}')
        print(f'Response Body:')

        try:
            body_json = json.loads(body)
            print(json.dumps(body_json, indent=2, ensure_ascii=False))
        except:
            print(body)
    else:
        print(result)

except Exception as e:
    print(f'ERROR: {str(e)}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo ""
echo "============================================"

if [ $? -eq 0 ]; then
    echo "✓ Execution completed successfully"
else
    echo "✗ Execution failed"
    exit 1
fi

echo ""
