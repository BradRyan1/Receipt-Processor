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
    
    # Enhanced total patterns - look for various receipt total indicators
    total_patterns = [
        # Primary total patterns
        r'total[:\s]*\$?(\d+\.?\d*)',
        r'grand\s+total[:\s]*\$?(\d+\.?\d*)',
        r'amount[:\s]*\$?(\d+\.?\d*)',
        r'value[:\s]*\$?(\d+\.?\d*)',
        r'balance[:\s]*\$?(\d+\.?\d*)',
        r'charge[:\s]*\$?(\d+\.?\d*)',
        r'payment[:\s]*\$?(\d+\.?\d*)',
        
        # Subtotal patterns (often the final amount)
        r'subtotal[:\s]*\$?(\d+\.?\d*)',
        r'sub\s*total[:\s]*\$?(\d+\.?\d*)',
        
        # Common receipt phrases
        r'amount\s+due[:\s]*\$?(\d+\.?\d*)',
        r'total\s+due[:\s]*\$?(\d+\.?\d*)',
        r'balance\s+due[:\s]*\$?(\d+\.?\d*)',
        r'final\s+total[:\s]*\$?(\d+\.?\d*)',
        r'final\s+amount[:\s]*\$?(\d+\.?\d*)',
        
        # Dollar amounts at end of lines (common in receipts)
        r'\$(\d+\.?\d*)\s*$',  # Dollar amount at end of line
        r'\$(\d+\.?\d*)\s*\n',  # Dollar amount followed by newline
        
        # Amounts with currency symbols
        r'[\$£€¥](\d+\.?\d*)',  # Various currency symbols
        
        # Amounts in parentheses (sometimes used for totals)
        r'\([\$£€¥]?(\d+\.?\d*)\)',
        
        # Amounts with "USD" or "CAD" etc.
        r'(\d+\.?\d*)\s*(USD|CAD|EUR|GBP)',
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
    
    # Extract total with enhanced logic
    extracted_total = None
    total_matches = []
    
    # First pass: collect all potential total matches
    for pattern in total_patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            try:
                amount = float(match.group(1))
                # Store match with pattern priority and position
                priority = 0
                if 'total' in pattern and 'grand' in pattern:
                    priority = 10  # Highest priority for grand total
                elif 'total' in pattern:
                    priority = 9   # High priority for total
                elif 'subtotal' in pattern:
                    priority = 8   # Good priority for subtotal
                elif 'amount' in pattern or 'value' in pattern:
                    priority = 7   # Medium priority for amount/value
                elif 'balance' in pattern or 'due' in pattern:
                    priority = 6   # Medium priority for balance/due
                else:
                    priority = 5   # Lower priority for other patterns
                
                total_matches.append({
                    'amount': amount,
                    'priority': priority,
                    'pattern': pattern,
                    'position': match.start(),
                    'match_text': match.group(0)
                })
            except (ValueError, IndexError):
                continue
    
    # Second pass: select the best total
    if total_matches:
        # Sort by priority (highest first), then by position (last in text first)
        total_matches.sort(key=lambda x: (x['priority'], -x['position']), reverse=True)
        
        # Take the highest priority match
        extracted_total = total_matches[0]['amount']
        
        # Log the selection for debugging
        logger.info(f"Selected total: ${extracted_total} from pattern '{total_matches[0]['pattern']}' "
                   f"at position {total_matches[0]['position']}")
    
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
                st.rerun()
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
    if folder_path:
        # Clean and normalize the path
        try:
            # Handle different path formats
            if folder_path.startswith('"') and folder_path.endswith('"'):
                folder_path = folder_path[1:-1]  # Remove quotes
            
            # Normalize path separators
            folder_path = os.path.normpath(folder_path)
            
            # Convert to absolute path if needed
            if not os.path.isabs(folder_path):
                folder_path = os.path.abspath(folder_path)
            
            # Check if path exists
            if os.path.exists(folder_path):
                st.success(f"✅ Folder found: {folder_path}")
                
                # Find image files
                image_files = []
                for ext in file_extensions:
                    try:
                        image_files.extend(Path(folder_path).glob(f"*{ext}"))
                        image_files.extend(Path(folder_path).glob(f"*{ext.upper()}"))
                    except Exception as e:
                        st.warning(f"Error searching for {ext} files: {str(e)}")
                
                if not image_files:
                    st.warning(f"No image files found in {folder_path} with selected extensions.")
                    st.info("Supported formats: JPG, JPEG, PNG, TIFF, BMP, PDF")
                    
                    # Show what files are actually in the folder
                    try:
                        all_files = list(Path(folder_path).iterdir())
                        if all_files:
                            st.info("Files found in folder:")
                            for file in all_files[:10]:  # Show first 10 files
                                st.write(f"• {file.name}")
                            if len(all_files) > 10:
                                st.write(f"... and {len(all_files) - 10} more files")
                    except Exception as e:
                        st.error(f"Error listing folder contents: {str(e)}")
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
                            
                            # Store results in session state for later use
                            st.session_state['processing_results'] = results
                            
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
            else:
                st.error(f"❌ Folder not found: {folder_path}")
                st.info("Please check the folder path and try again.")
                
                # Provide helpful debugging info
                st.subheader("🔍 Debug Information")
                st.write(f"**Path entered:** {folder_path}")
                st.write(f"**Path exists:** {os.path.exists(folder_path)}")
                st.write(f"**Is absolute:** {os.path.isabs(folder_path)}")
                
                # Check if parent directory exists
                parent_dir = os.path.dirname(folder_path)
                if os.path.exists(parent_dir):
                    st.write(f"✅ Parent directory exists: {parent_dir}")
                    try:
                        parent_contents = os.listdir(parent_dir)
                        st.write(f"**Contents of parent directory:**")
                        for item in parent_contents[:10]:
                            st.write(f"• {item}")
                        if len(parent_contents) > 10:
                            st.write(f"... and {len(parent_contents) - 10} more items")
                    except Exception as e:
                        st.error(f"Error listing parent directory: {str(e)}")
                else:
                    st.write(f"❌ Parent directory does not exist: {parent_dir}")
                
        except Exception as e:
            st.error(f"❌ Error processing folder path: {str(e)}")
            st.info("Please try entering the path manually or use the Browse button.")
    else:
        st.info("👈 Please select a folder using the Browse button or enter a folder path to get started.")
    
    # Show rename button if we have results
    if 'processing_results' in st.session_state and st.session_state['processing_results']:
        st.header("📝 File Renaming")
        results = st.session_state['processing_results']
        
        # Count files that can be renamed
        renameable_files = [r for r in results if r['new_filename'] and not r['error']]
        
        if renameable_files:
            st.info(f"Found {len(renameable_files)} files that can be renamed.")
            
            # Show preview of what will be renamed
            with st.expander("📋 Preview Renames"):
                for result in renameable_files:
                    old_name = Path(result['file_path']).name
                    new_name = f"{result['new_filename']}{Path(result['file_path']).suffix}"
                    st.write(f"• {old_name} → {new_name}")
            
            # Rename button
            if st.button("📝 Rename Files", type="secondary"):
                rename_progress = st.progress(0)
                rename_status = st.empty()
                
                successful_renames = 0
                failed_renames = []
                
                for i, result in enumerate(renameable_files):
                    old_name = Path(result['file_path']).name
                    rename_status.text(f"Renaming {old_name}...")
                    
                    try:
                        if rename_file(result['file_path'], result['new_filename']):
                            successful_renames += 1
                            st.success(f"✅ Renamed: {old_name}")
                        else:
                            failed_renames.append(old_name)
                            st.error(f"❌ Failed to rename: {old_name}")
                    except Exception as e:
                        failed_renames.append(old_name)
                        st.error(f"❌ Error renaming {old_name}: {str(e)}")
                    
                    rename_progress.progress((i + 1) / len(renameable_files))
                
                rename_status.text(f"Renaming complete! {successful_renames} files renamed successfully.")
                
                if successful_renames > 0:
                    st.success(f"✅ {successful_renames} files renamed successfully!")
                    
                    # Show summary
                    st.subheader("📊 Rename Summary")
                    st.write(f"**Successfully renamed:** {successful_renames} files")
                    
                    if failed_renames:
                        st.write(f"**Failed to rename:** {len(failed_renames)} files")
                        with st.expander("Failed files"):
                            for failed_file in failed_renames:
                                st.write(f"• {failed_file}")
                    
                    # Update session state with new file paths
                    st.session_state['processing_results'] = results
                    st.rerun()
                else:
                    st.error("❌ No files were renamed. Check the error messages above.")
        else:
            st.warning("No files can be renamed. Make sure files were processed successfully and have valid classifications, dates, and totals.")
    
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