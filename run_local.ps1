# Local execution script for PatentAgent Lambda handler
# Usage: ./run_local.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PatentAgent - Local Execution Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create .env file from .env.example:" -ForegroundColor Yellow
    Write-Host "  cp .env.example .env" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then edit .env with your credentials:" -ForegroundColor Yellow
    Write-Host "  - JPO_API_ID" -ForegroundColor Gray
    Write-Host "  - JPO_API_PASSWORD" -ForegroundColor Gray
    Write-Host "  - SLACK_WEBHOOK_URL" -ForegroundColor Gray
    exit 1
}

Write-Host "✓ .env file found" -ForegroundColor Green
Write-Host ""

# Check if requirements are installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
$packages = @("requests", "python-dotenv", "boto3")
$missing = @()

foreach ($package in $packages) {
    $result = python -c "import $($package.Replace('-', '_'))" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missing += $package
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing packages: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ All dependencies installed" -ForegroundColor Green
Write-Host ""

# Run the handler
Write-Host "Executing Lambda handler..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

python -c "
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

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Execution completed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Execution failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
