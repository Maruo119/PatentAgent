#!/usr/bin/env python3
"""
Local test script for PatentAgent Lambda handler.
Run this script to test the patent agent locally before AWS deployment.

Usage:
    python test_local.py
"""

import sys
import os
import json
from pathlib import Path

def check_env_file():
    """Check if .env file exists."""
    if not Path('.env').exists():
        print("ERROR: .env file not found!")
        print("")
        print("Please create .env file from .env.example:")
        print("  cp .env.example .env")
        print("")
        print("Then edit .env with your credentials:")
        print("  - JPO_API_ID")
        print("  - JPO_API_PASSWORD")
        print("  - SLACK_WEBHOOK_URL")
        return False
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = ['requests', 'python-dotenv', 'boto3']
    missing = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("")
        print("Installing dependencies...")
        import subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
            capture_output=True
        )
        if result.returncode != 0:
            print("ERROR: Failed to install dependencies")
            return False
    return True

def run_handler():
    """Run the Lambda handler locally."""
    # Setup path
    project_root = Path(__file__).parent.absolute()
    lambda_dir = project_root / 'src' / 'lambda'

    sys.path.insert(0, str(lambda_dir))
    os.chdir(str(lambda_dir))

    # Load environment variables
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    load_dotenv(str(env_file))

    # Import and run handler
    from handler import lambda_handler

    try:
        print("Executing Lambda handler...")
        print("=" * 60)
        print("")

        result = lambda_handler({}, None)

        # Display result
        if isinstance(result, dict):
            status_code = result.get('statusCode', 'N/A')
            body = result.get('body', '{}')

            print(f'Status Code: {status_code}')
            print('')
            print('Response Body:')

            try:
                body_json = json.loads(body)
                print(json.dumps(body_json, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(body)
        else:
            print(result)

        print("")
        print("=" * 60)
        print("[OK] Execution completed successfully")
        print("")
        return True

    except Exception as e:
        print(f'ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print("=" * 60)
    print("PatentAgent - Local Test Script")
    print("=" * 60)
    print("")

    # Validation checks
    print("Checking .env file...")
    if not check_env_file():
        return 1

    print("[OK] .env file found")
    print("")

    print("Checking dependencies...")
    if not check_dependencies():
        return 1

    print("[OK] All dependencies installed")
    print("")

    # Run handler
    if run_handler():
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())
