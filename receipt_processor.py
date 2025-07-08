import streamlit as st
import boto3
import os
import re
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional
import logging
import tkinter as tk
from tkinter import filedialog
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def select_folder():
    """Open folder selection dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Bring dialog to front
    
    folder_path = filedialog.askdirectory(
        title="Select folder containing receipt images",
        initialdir=os.path.expanduser("~")  # Start from user's home directory
    )
    
    root.destroy()
    return folder_path

# Initialize AWS clients
@st.cache_resource
def init_aws_clients():
    """Initialize AWS clients using configured credentials"""
    try:
        textract = boto3.client('textract', region_name='us-east-1')
        comprehend = boto3.client('comprehend', region_name='us-east-1')
        return textract, comprehend
    except Exception as e:
        logger.error(f"Failed to initialize AWS clients: {str(e)}")
        return None, None

def extract_text_from_image(textract_client, image_path: str) -> str:
    """Extract text from an image using Amazon Textract"""
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File not found: {image_path}")
        if not os.access(image_path, os.R_OK):
            raise PermissionError(f"No read permission for file: {image_path}")
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()
        
        response = textract_client.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        extracted_text = ' '.join([item['Text'] for item in response['Blocks'] if item['BlockType'] == 'LINE'])
        return extracted_text
    except FileNotFoundError as fnf:
        logger.error(str(fnf))
        return f"ERROR: {str(fnf)}"
    except PermissionError as pe:
        logger.error(str(pe))
        return f"ERROR: {str(pe)}"
    except Exception as e:
        logger.error(f"Error extracting text from {image_path}: {str(e)}")
        return f"ERROR: {str(e)}"

def classify_receipt(comprehend_client, text: str) -> str:
    """Classify receipt type using Amazon Comprehend"""
    try:
        # Keywords for different receipt types
        receipt_keywords = {
            'Restaurant': ['restaurant', 'cafe', 'dining', 'food', 'meal', 'grill', 'pizza', 'burger', 'sushi'],
            'Parking': ['parking', 'garage', 'valet', 'meter', 'lot'],
            'Gas': ['gas', 'fuel', 'petrol', 'station', 'shell', 'exxon', 'bp', 'chevron'],
            'Grocery': ['grocery', 'supermarket', 'market', 'food', 'walmart', 'target', 'kroger', 'safeway'],
            'Retail': ['store', 'shop', 'retail', 'clothing', 'electronics', 'amazon', 'best buy'],
            'Transportation': ['uber', 'lyft', 'taxi', 'transport', 'bus', 'train', 'subway'],
            'Entertainment': ['movie', 'theater', 'cinema', 'concert', 'show', 'ticket', 'amusement'],
            'Healthcare': ['pharmacy', 'drug', 'medical', 'doctor', 'hospital', 'clinic', 'cvs', 'walgreens'],
            'Utilities': ['electric', 'water', 'gas', 'internet', 'phone', 'utility', 'bill']
        }
        
        # Use Comprehend to detect entities and key phrases
        entities_response = comprehend_client.detect_entities(Text=text, LanguageCode='en')
        key_phrases_response = comprehend_client.detect_key_phrases(Text=text, LanguageCode='en')
        
        # Combine all detected text
        all_text = text.lower()
        entity_text = ' '.join([entity['Text'].lower() for entity in entities_response['Entities']])
        phrase_text = ' '.join([phrase['Text'].lower() for phrase in key_phrases_response['KeyPhrases']])
        
        combined_text = f"{all_text} {entity_text} {phrase_text}"
        
        # Score each receipt type
        scores = {}
        for receipt_type, keywords in receipt_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            scores[receipt_type] = score
        
        # Return the type with highest score, default to 'Other' if no match
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return 'Other'
            
    except Exception as e:
        logger.error(f"Error classifying receipt: {str(e)}")
        return 'Other'

def extract_date_and_total(text: str) -> Tuple[Optional[str], Optional[float]]:
    """Extract date and total amount from receipt text"""
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{2,4})',  # DD Month YYYY
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s+(\d{2,4})',  # Month DD, YYYY
    ]
    
    total_patterns = [
        r'total[:\s]*\$?(\d+\.?\d*)',
        r'amount[:\s]*\$?(\d+\.?\d*)',
        r'balance[:\s]*\$?(\d+\.?\d*)',
        r'grand\s+total[:\s]*\$?(\d+\.?\d*)',
        r'\$(\d+\.?\d*)\s*$',  # Dollar amount at end of line
    ]
    
    # Extract date
    extracted_date = None
    for pattern in date_patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                if 'jan' in pattern or 'feb' in pattern:  # Month name pattern
                    month_map = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    if len(match.groups()) == 3:
                        if match.group(1).isdigit():
                            day, month_name, year = match.groups()
                        else:
                            month_name, day, year = match.groups()
                        month = month_map.get(month_name[:3], 1)
                        year = int(year) if len(year) == 4 else int('20' + year)
                        extracted_date = datetime(year, month, int(day)).strftime('%d %B %Y')
                else:  # Numeric date pattern
                    groups = match.groups()
                    if len(groups) == 3:
                        if int(groups[0]) <= 12:  # MM/DD/YYYY
                            month, day, year = groups
                        else:  # DD/MM/YYYY
                            day, month, year = groups
                        year = int(year) if len(year) == 4 else int('20' + year)
                        extracted_date = datetime(year, int(month), int(day)).strftime('%d %B %Y')
                break
            except (ValueError, IndexError):
                continue
    
    # Extract total
    extracted_total = None
    for pattern in total_patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                extracted_total = float(match.group(1))
                break
            except (ValueError, IndexError):
                continue
    
    return extracted_date, extracted_total

def process_receipt_file(textract_client, comprehend_client, file_path: str) -> Dict:
    """Process a single receipt file and return extracted information"""
    try:
        # Extract text from image
        extracted_text = extract_text_from_image(textract_client, file_path)
        
        if extracted_text.startswith("ERROR:"):
            return {
                'file_path': file_path,
                'classification': 'File Error',
                'date': None,
                'total': None,
                'new_filename': None,
                'extracted_text': extracted_text,
                'error': extracted_text
            }
        
        if not extracted_text:
            return {
                'file_path': file_path,
                'classification': 'Unknown',
                'date': None,
                'total': None,
                'new_filename': None,
                'extracted_text': '',
                'error': 'No text extracted'
            }
        
        # Classify receipt
        classification = classify_receipt(comprehend_client, extracted_text)
        
        # Extract date and total
        date, total = extract_date_and_total(extracted_text)
        
        # Generate new filename
        new_filename = None
        if classification and date and total:
            new_filename = f"{classification} - {date} - ${total:.2f}"
        elif classification and date:
            new_filename = f"{classification} - {date}"
        elif classification and total:
            new_filename = f"{classification} - ${total:.2f}"
        elif classification:
            new_filename = f"{classification}"
        
        return {
            'file_path': file_path,
            'classification': classification,
            'date': date,
            'total': total,
            'new_filename': new_filename,
            'extracted_text': extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return {
            'file_path': file_path,
            'classification': 'Error',
            'date': None,
            'total': None,
            'new_filename': None,
            'error': str(e)
        }

def rename_file(old_path: str, new_filename: str) -> bool:
    """Rename file with new filename"""
    try:
        if not new_filename:
            return False
            
        # Clean filename for filesystem
        clean_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename)
        file_extension = Path(old_path).suffix
        new_path = Path(old_path).parent / f"{clean_filename}{file_extension}"
        
        # Handle duplicate filenames
        counter = 1
        original_new_path = new_path
        while new_path.exists():
            new_path = Path(str(original_new_path).replace(file_extension, f"_{counter}{file_extension}"))
            counter += 1
        
        os.rename(old_path, new_path)
        return True
    except Exception as e:
        logger.error(f"Error renaming file {old_path}: {str(e)}")
        return False

def main():
    st.set_page_config(
        page_title="Receipt Processor",
        page_icon="🧾",
        layout="wide"
    )
    
    st.title("🧾 Receipt Processor")
    st.markdown("Upload receipts and automatically classify, extract dates, and rename files using Amazon Textract and Comprehend")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # AWS Status Check
    st.sidebar.subheader("AWS Status")
    try:
        textract_client, comprehend_client = init_aws_clients()
        if textract_client and comprehend_client:
            st.sidebar.success("✅ AWS Connected")
        else:
            st.sidebar.error("❌ AWS Connection Failed")
            st.sidebar.info("Please check your AWS credentials with 'aws configure'")
    except Exception as e:
        st.sidebar.error(f"❌ AWS Error: {str(e)}")
        textract_client = None
        comprehend_client = None
    
    # Folder selection with browse button
    st.sidebar.subheader("📁 Folder Selection")
    
    # Initialize session state for folder_path if not set
    if 'folder_path' not in st.session_state:
        st.session_state['folder_path'] = ''
    
    # Handle Browse button
    browse_clicked = st.sidebar.button("📂 Browse", help="Click to browse and select a folder")
    if browse_clicked:
        try:
            selected_folder = select_folder()
            if selected_folder:
                st.session_state['folder_path'] = selected_folder
                st.experimental_rerun()
        except Exception as e:
            st.sidebar.error(f"Error opening folder dialog: {str(e)}")
    
    # Folder path input (value comes from session state)
    folder_path = st.sidebar.text_input(
        "Folder path:",
        value=st.session_state['folder_path'],
        placeholder="Select folder with receipt images"
    )
    # Keep session state in sync if user types manually
    if folder_path != st.session_state['folder_path']:
        st.session_state['folder_path'] = folder_path
    
    # File type filter
    st.sidebar.subheader("📄 File Types")
    file_extensions = st.sidebar.multiselect(
        "Select file types to process:",
        ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.pdf'],
        default=['.jpg', '.jpeg', '.png']
    )
    
    # Processing options
    st.sidebar.subheader("⚙️ Processing Options")
    auto_rename = st.sidebar.checkbox("Automatically rename files", value=True)
    show_extracted_text = st.sidebar.checkbox("Show extracted text", value=False)
    
    # Main content area
    if folder_path and os.path.exists(folder_path):
        st.success(f"✅ Folder found: {folder_path}")
        
        # Find image files
        image_files = []
        for ext in file_extensions:
            image_files.extend(Path(folder_path).glob(f"*{ext}"))
            image_files.extend(Path(folder_path).glob(f"*{ext.upper()}"))
        
        if not image_files:
            st.warning(f"No image files found in {folder_path} with selected extensions.")
            st.info("Supported formats: JPG, JPEG, PNG, TIFF, BMP, PDF")
        else:
            st.info(f"Found {len(image_files)} image files to process.")
            
            # Show preview of files
            with st.expander(f"📋 Preview Files ({len(image_files)} found)"):
                file_list = [f.name for f in image_files[:10]]  # Show first 10 files
                if len(image_files) > 10:
                    file_list.append(f"... and {len(image_files) - 10} more files")
                for file_name in file_list:
                    st.write(f"• {file_name}")
            
            # Check AWS status before allowing processing
            if not textract_client or not comprehend_client:
                st.error("❌ AWS services not available. Cannot process receipts.")
                st.info("Please configure your AWS credentials using 'aws configure'")
                st.info("See aws_setup_guide.md for detailed instructions.")
            else:
                # Process button
                if st.button("🚀 Process Receipts", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results = []
                    
                    for i, file_path in enumerate(image_files):
                        status_text.text(f"Processing {file_path.name}...")
                        
                        result = process_receipt_file(textract_client, comprehend_client, str(file_path))
                        results.append(result)
                        
                        # Update progress
                        progress_bar.progress((i + 1) / len(image_files))
                    
                    status_text.text("Processing complete!")
                    
                    # Display results
                    st.header("📊 Processing Results")
                    
                    # Summary statistics
                    classifications = [r['classification'] for r in results if r['classification'] != 'Error']
                    if classifications:
                        st.subheader("Receipt Classifications")
                        classification_counts = {}
                        for classification in classifications:
                            classification_counts[classification] = classification_counts.get(classification, 0) + 1
                        
                        for classification, count in classification_counts.items():
                            st.write(f"• {classification}: {count} receipts")
                    
                    # Detailed results table
                    st.subheader("Detailed Results")
                    
                    # Prepare data for display
                    display_data = []
                    for result in results:
                        display_data.append({
                            'File': Path(result['file_path']).name,
                            'Classification': result['classification'],
                            'Date': result['date'] or 'Not found',
                            'Total': f"${result['total']:.2f}" if result['total'] else 'Not found',
                            'New Filename': result['new_filename'] or 'Not generated',
                            'Status': '✅ Success' if not result['error'] else f"❌ {result['error']}"
                        })
                    
                    st.dataframe(display_data, use_container_width=True)
                    
                    # Show extracted text if requested
                    if show_extracted_text:
                        st.subheader("Extracted Text Samples")
                        for result in results:
                            if result['extracted_text'] and not result['error']:
                                with st.expander(f"Text from {Path(result['file_path']).name}"):
                                    st.text(result['extracted_text'])
                    
                    # Rename files if requested
                    if auto_rename and st.button("📝 Rename Files"):
                        rename_progress = st.progress(0)
                        rename_status = st.empty()
                        
                        successful_renames = 0
                        for i, result in enumerate(results):
                            if result['new_filename'] and not result['error']:
                                rename_status.text(f"Renaming {Path(result['file_path']).name}...")
                                if rename_file(result['file_path'], result['new_filename']):
                                    successful_renames += 1
                            
                            rename_progress.progress((i + 1) / len(results))
                        
                        rename_status.text(f"Renaming complete! {successful_renames} files renamed successfully.")
                        st.success(f"✅ {successful_renames} files renamed successfully!")
                        
                        # Show new filenames
                        if successful_renames > 0:
                            st.subheader("Renamed Files")
                            for result in results:
                                if result['new_filename'] and not result['error']:
                                    st.write(f"• {Path(result['file_path']).name} → {result['new_filename']}")
    
    elif folder_path:
        st.error(f"❌ Folder not found: {folder_path}")
        st.info("Please enter a valid folder path or use the Browse button.")
    else:
        st.info("👈 Please select a folder using the Browse button or enter a folder path to get started.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        **How it works:**
        1. **Text Extraction**: Uses Amazon Textract to extract text from receipt images
        2. **Classification**: Uses Amazon Comprehend to classify receipts by type
        3. **Data Extraction**: Extracts dates and total amounts using pattern matching
        4. **File Renaming**: Renames files with structured format: "Type - Date - Amount"
        
        **Supported file types:** JPG, JPEG, PNG, TIFF, BMP, PDF
        """
    )

if __name__ == "__main__":
    main() 