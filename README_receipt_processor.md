# Receipt Processor App

A Streamlit application that uses Amazon Textract and Comprehend to automatically process, classify, and rename receipt images.

## Features

- **Text Extraction**: Uses Amazon Textract to extract text from receipt images
- **Receipt Classification**: Uses Amazon Comprehend to classify receipts by type (Restaurant, Parking, Gas, etc.)
- **Data Extraction**: Automatically extracts dates and total amounts from receipts
- **File Renaming**: Renames files with structured format: "Type - Date - Amount"
- **Batch Processing**: Process multiple receipts at once
- **Interactive UI**: User-friendly Streamlit interface

## Prerequisites

1. **AWS Account**: You need an AWS account with access to Amazon Textract and Comprehend
2. **AWS Credentials**: Configure your AWS credentials using `aws configure`
3. **Python**: Python 3.7 or higher
4. **Required Permissions**: Your AWS user/role needs permissions for:
   - `textract:DetectDocumentText`
   - `comprehend:DetectEntities`
   - `comprehend:DetectKeyPhrases`

## Installation

1. **Clone or download the files** to your local machine

2. **Install dependencies**:
   ```bash
   pip install -r receipt_processor_requirements.txt
   ```

3. **Configure AWS credentials**:
   ```bash
   aws configure
   ```
   Enter your:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., us-east-1)
   - Default output format (json)

## Usage

1. **Run the application**:
   ```bash
   streamlit run receipt_processor.py
   ```

2. **Open your browser** and navigate to the URL shown in the terminal (usually http://localhost:8501)

3. **Configure settings** in the sidebar:
   - Enter the folder path containing your receipt images
   - Select file types to process (JPG, PNG, etc.)
   - Choose processing options

4. **Process receipts**:
   - Click "Process Receipts" to analyze all images
   - Review the results in the detailed table
   - Optionally rename files automatically

## Supported Receipt Types

The app can classify receipts into the following categories:
- **Restaurant**: Dining, cafes, food services
- **Parking**: Parking garages, meters, lots
- **Gas**: Fuel stations, gas stations
- **Grocery**: Supermarkets, food stores
- **Retail**: General retail stores
- **Transportation**: Uber, Lyft, taxis, public transport
- **Entertainment**: Movies, concerts, shows
- **Healthcare**: Pharmacies, medical services
- **Utilities**: Bills, services
- **Other**: Unclassified receipts

## File Naming Convention

Processed files are renamed using the format:
```
[Classification] - [Date] - $[Amount]
```

Examples:
- `Restaurant - 15 June 2024 - $45.67`
- `Parking - 20 June 2024 - $12.00`
- `Gas - 25 June 2024 - $35.89`

## Supported File Formats

- JPG/JPEG
- PNG
- TIFF
- BMP
- PDF

## Troubleshooting

### AWS Credentials Issues
- Ensure you've run `aws configure` correctly
- Check that your AWS user has the necessary permissions
- Verify your region settings

### No Text Extracted
- Ensure images are clear and readable
- Check that text is not too small or blurry
- Try different image formats

### Classification Issues
- The app uses keyword matching and AI classification
- Some receipts may be classified as "Other" if they don't match known patterns
- You can manually review and adjust classifications

### File Renaming Issues
- Ensure you have write permissions in the target folder
- Check that filenames don't contain invalid characters
- The app will automatically handle duplicate filenames

## Security Notes

- AWS credentials are used locally and not stored in the application
- Images are processed locally and not uploaded to AWS (only text is sent)
- Consider using AWS IAM roles with minimal required permissions

## Cost Considerations

- Amazon Textract: Charged per page processed
- Amazon Comprehend: Charged per unit of text processed
- Check AWS pricing for current rates in your region

## Customization

You can modify the receipt classification keywords in the `classify_receipt` function to better match your specific receipt types and vendors.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your AWS setup and permissions
3. Ensure all dependencies are installed correctly 