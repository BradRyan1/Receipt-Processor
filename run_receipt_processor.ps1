# Receipt Processor Launcher Script
Write-Host "🧾 Receipt Processor App" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.7 or higher." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if AWS CLI is configured
try {
    $awsIdentity = aws sts get-caller-identity 2>&1
    if ($awsIdentity -match "Account") {
        Write-Host "✅ AWS credentials configured" -ForegroundColor Green
    } else {
        throw "AWS not configured"
    }
} catch {
    Write-Host "❌ AWS credentials not configured." -ForegroundColor Red
    Write-Host "Please run: aws configure" -ForegroundColor Yellow
    Write-Host "See aws_setup_guide.md for detailed instructions." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if requirements are installed
Write-Host "📦 Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import streamlit, boto3" 2>&1 | Out-Null
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Missing dependencies. Installing..." -ForegroundColor Red
    pip install -r receipt_processor_requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "🚀 Starting Receipt Processor..." -ForegroundColor Green
Write-Host "The app will open in your default browser." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the app." -ForegroundColor Yellow
Write-Host ""

# Start the Streamlit app
streamlit run receipt_processor.py 