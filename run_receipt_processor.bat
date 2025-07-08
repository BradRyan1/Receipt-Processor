@echo off
echo Starting Receipt Processor App...
echo.
echo Make sure you have:
echo 1. Python installed
echo 2. AWS credentials configured (aws configure)
echo 3. Dependencies installed (pip install -r receipt_processor_requirements.txt)
echo.
pause
streamlit run receipt_processor.py
pause 