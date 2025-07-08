# 🚀 Quick Start Guide - Receipt Processor

## What You Have

A complete Streamlit application that automatically processes receipt images using Amazon AWS services:

- **📸 Text Extraction**: Amazon Textract extracts text from receipt images
- **🏷️ Classification**: Amazon Comprehend classifies receipts by type
- **📅 Date Extraction**: Automatically finds receipt dates
- **💰 Amount Extraction**: Extracts total amounts
- **📝 File Renaming**: Renames files to "Type - Date - Amount" format

## Files Created

1. **`receipt_processor.py`** - Main Streamlit application
2. **`receipt_processor_requirements.txt`** - Python dependencies
3. **`README_receipt_processor.md`** - Detailed documentation
4. **`aws_setup_guide.md`** - AWS configuration guide
5. **`run_receipt_processor.bat`** - Windows batch launcher
6. **`run_receipt_processor.ps1`** - PowerShell launcher with checks

## 🎯 3-Step Setup

### Step 1: Configure AWS
```bash
aws configure
```
Enter your AWS Access Key ID, Secret Access Key, and region (e.g., us-east-1)

### Step 2: Install Dependencies
```bash
pip install -r receipt_processor_requirements.txt
```

### Step 3: Run the App
```bash
streamlit run receipt_processor.py
```

## 🎮 How to Use

1. **Enter folder path** containing your receipt images
2. **Select file types** (JPG, PNG, etc.)
3. **Click "Process Receipts"**
4. **Review results** in the table
5. **Rename files** automatically (optional)

## 📁 Example Output

Your receipt files will be renamed like:
- `Restaurant - 15 June 2024 - $45.67.jpg`
- `Parking - 20 June 2024 - $12.00.png`
- `Gas - 25 June 2024 - $35.89.jpg`

## 🔧 Supported Receipt Types

- Restaurant, Parking, Gas, Grocery, Retail
- Transportation, Entertainment, Healthcare, Utilities
- Automatically classified using AI

## 💡 Pro Tips

- **Clear images** work best for text extraction
- **Multiple formats** supported: JPG, PNG, TIFF, BMP, PDF
- **Batch processing** handles multiple receipts at once
- **Error handling** shows which files couldn't be processed
- **Cost aware** - only processes text, not images

## 🆘 Need Help?

1. Check `aws_setup_guide.md` for AWS configuration
2. Review `README_receipt_processor.md` for detailed instructions
3. Ensure your AWS user has Textract and Comprehend permissions

## 💰 Cost Estimate

- **Textract**: ~$1.50 per 1,000 pages
- **Comprehend**: ~$0.0001 per unit (100 characters)
- Typical receipt: ~$0.002-0.005 per receipt

Ready to process your receipts! 🧾✨ 