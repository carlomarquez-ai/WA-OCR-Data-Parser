import re
import easyocr
import os
import pandas as pd
from datetime import datetime
import json

# ===== Load Settings =====
try:
    import setting
    SETTINGS = {
        'SOURCE_DIR': getattr(setting, 'SOURCE_DIR', 'source_image'),
        'OUTPUT_EXCEL': getattr(setting, 'OUTPUT_EXCEL', 'result.xlsx'),
        'LANGUAGES': getattr(setting, 'LANGUAGES', ['en', 'ar']),
        'USE_GPU': getattr(setting, 'USE_GPU', False)
    }
except ModuleNotFoundError:
    SETTINGS = {
        'SOURCE_DIR': 'source_image',
        'OUTPUT_EXCEL': 'result.xlsx',
        'LANGUAGES': ['en', 'ar'],
        'USE_GPU': False
    }

# ===== Save current settings to setting.py =====
def save_settings():
    content = f"""# Auto-generated settings

SOURCE_DIR = '{SETTINGS['SOURCE_DIR']}'
OUTPUT_EXCEL = '{SETTINGS['OUTPUT_EXCEL']}'
LANGUAGES = {SETTINGS['LANGUAGES']}
USE_GPU = {SETTINGS['USE_GPU']}
"""
    with open('setting.py', 'w', encoding='utf-8') as f:
        f.write(content)

save_settings()

# ===== OCR & Extraction =====
def extract_phone_numbers_global(text):
    """
    Extract phone numbers from various countries and formats.
    """
    phone_numbers = []
    
    # Pattern 1: International format with + and country code (1-3 digits)
    # Matches: +1234567890, +44 20 1234 5678, +91-98765-43210, etc.
    pattern1 = r'\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}'
    
    # Pattern 2: International format without + but with country code
    # Matches: 966501234567, 1 234 567 8900, etc.
    pattern2 = r'\b\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b'
    
    # Pattern 3: Local formats (10+ digits with optional separators)
    # Matches: 0501234567, 050-123-4567, (050) 123-4567, etc.
    pattern3 = r'\b[\(]?0\d{1,3}[\)]?[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b'
    
    # Pattern 4: Simple 10+ digit sequences
    pattern4 = r'\b\d{10,15}\b'
    
    all_patterns = [pattern1, pattern2, pattern3, pattern4]
    
    for pattern in all_patterns:
        matches = re.findall(pattern, text)
        phone_numbers.extend(matches)
    
    # Clean and normalize phone numbers
    cleaned_numbers = []
    seen = set()
    
    for number in phone_numbers:
        # Remove all spaces, hyphens, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', number)
        
        # Skip if too short (less than 8 digits) or too long (more than 15)
        if len(cleaned) < 8 or len(cleaned) > 15:
            continue
        
        # Skip if it's all zeros or repetitive
        if cleaned == '0' * len(cleaned):
            continue
        
        # Normalize: ensure it starts with +
        if not cleaned.startswith('+'):
            # If starts with 00, replace with +
            if cleaned.startswith('00'):
                cleaned = '+' + cleaned[2:]
            # If starts with 0 and is 10 digits (likely local Saudi number)
            elif cleaned.startswith('0') and len(cleaned) == 10:
                cleaned = '+966' + cleaned[1:]
            # If starts with 966 (Saudi without +)
            elif cleaned.startswith('966'):
                cleaned = '+' + cleaned
            # Otherwise, try to add + if it looks international
            elif len(cleaned) >= 10:
                cleaned = '+' + cleaned
        
        # Avoid duplicates
        if cleaned not in seen:
            seen.add(cleaned)
            cleaned_numbers.append(cleaned)
    
    return cleaned_numbers


def extract_info_from_image(image_path, reader):
    result = reader.readtext(image_path)
    
    all_detections = []
    all_text = []
    
    for detection in result:
        bbox, text, confidence = detection
        all_detections.append({
            'text': text,
            'confidence': confidence,
            'y_position': bbox[0][1]
        })
        all_text.append(text)
    
    all_detections.sort(key=lambda x: x['y_position'])
    full_text = ' '.join(all_text)
    
    # Extract phone numbers using global pattern
    phone_numbers = extract_phone_numbers_global(full_text)
    
    # Timestamp extraction
    day_pattern = r'Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|الأحد|الإثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت'
    time_pattern = r'\d{1,2}:\d{2}'
    arabic_time_pattern = r'اخر \d+ ساعه'
    
    day_match = re.search(day_pattern, full_text)
    time_match = re.search(time_pattern, full_text)
    arabic_time_match = re.search(arabic_time_pattern, full_text)
    
    timestamp = ''
    if day_match and time_match:
        timestamp = f"{day_match.group()} {time_match.group()}"
    elif day_match:
        timestamp = day_match.group()
    elif time_match:
        timestamp = time_match.group()
    elif arabic_time_match:
        timestamp = arabic_time_match.group()
    
    # Potential names (top banner - more precise)
    potential_names = []
    if all_detections:
        # Sort by Y position to get top-most text
        sorted_detections = sorted(all_detections, key=lambda x: x['y_position'])
        
        # Check first 3-5 text blocks (header area)
        for det in sorted_detections[:5]:
            text = det['text'].strip()
            
            # Skip if it looks like a phone number (contains many digits)
            digit_count = sum(c.isdigit() for c in text)
            if digit_count > 5:
                continue
            
            # Skip timestamps (day names and time)
            if re.search(r'Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday', text):
                continue
            if re.search(r'الأحد|الإثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت', text):
                continue
            if re.search(r'^\d{1,2}:\d{2}
    
    # Arabic messages
    arabic_pattern = r'[\u0600-\u06FF\s]+'
    arabic_texts = [t.strip() for t in re.findall(arabic_pattern, full_text) if len(t.strip()) > 5]
    
    return {
        'phone_numbers': phone_numbers,
        'names': potential_names,
        'timestamp': timestamp,
        'messages': arabic_texts,
        'all_text': full_text,
        'total_text_blocks': len(all_detections)
    }

# ===== Main Processing =====
def process_all_images():
    source_dir = SETTINGS['SOURCE_DIR']
    output_excel = SETTINGS['OUTPUT_EXCEL']
    
    if not os.path.exists(source_dir):
        print(f"Error: Directory '{source_dir}' not found!")
        return
    
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    image_files = [f for f in os.listdir(source_dir) if os.path.splitext(f.lower())[1] in image_extensions]
    
    if not image_files:
        print(f"No images found in '{source_dir}' directory!")
        return
    
    print(f"Found {len(image_files)} images to process")
    print("Initializing EasyOCR (this may take a moment)...")
    
    reader = easyocr.Reader(SETTINGS['LANGUAGES'], gpu=SETTINGS['USE_GPU'])
    
    phone_data, summary_data, all_text_data = [], [], []
    
    print("\nProcessing images...")
    print("-" * 70)
    
    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(source_dir, image_file)
        print(f"{idx}/{len(image_files)} Processing: {image_file}")
        try:
            info = extract_info_from_image(image_path, reader)
            
            if info['phone_numbers']:
                print(f"  ✓ Found {len(info['phone_numbers'])} phone numbers")
            else:
                print(f"  ⚠ No phone numbers found")
            
            # Phone sheet
            for phone in info['phone_numbers']:
                phone_data.append({
                    'Image_Name': image_file,
                    'Phone_Number': phone,
                    'Name': ', '.join(info['names']) if info['names'] else '',
                    'Timestamp': info['timestamp']
                })
            
            # Summary
            summary_data.append({
                'Image_Name': image_file,
                'Phone_Numbers_Count': len(info['phone_numbers']),
                'Names_Detected': ', '.join(info['names']) if info['names'] else 'None',
                'Timestamp': info['timestamp'] if info['timestamp'] else 'None',
                'Text_Blocks_Count': info['total_text_blocks']
            })
            
            # All text
            all_text_data.append({
                'Image_Name': image_file,
                'All_Extracted_Text': info['all_text'],
                'Arabic_Messages': ' | '.join(info['messages']) if info['messages'] else 'None'
            })
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            summary_data.append({
                'Image_Name': image_file,
                'Phone_Numbers_Count': 0,
                'Names_Detected': f'Error: {e}',
                'Timestamp': 'Error',
                'Text_Blocks_Count': 0
            })
    
    print("-" * 70)
    
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        if phone_data:
            pd.DataFrame(phone_data).to_excel(writer, sheet_name='Phone Numbers', index=False)
            unique_phones = list(set(d['Phone_Number'] for d in phone_data))
            pd.DataFrame({'Unique_Phone_Numbers': sorted(unique_phones)}).to_excel(writer, sheet_name='Unique Numbers', index=False)
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        pd.DataFrame(all_text_data).to_excel(writer, sheet_name='All Text', index=False)
    
    total_numbers = len(phone_data)
    unique_count = len(set(d['Phone_Number'] for d in phone_data)) if phone_data else 0
    
    print(f"\n✓ Processing complete!")
    print(f"  Total images processed: {len(image_files)}")
    print(f"  Total phone numbers found: {total_numbers}")
    print(f"  Unique phone numbers: {unique_count}")
    print(f"  Results saved to: {output_excel}")
    print(f"\nExcel sheets created:")
    print(f"  1. Phone Numbers - Phone numbers with name and timestamp")
    print(f"  2. Unique Numbers - Deduplicated phone numbers only")
    print(f"  3. Summary - Overview of each image")
    print(f"  4. All Text - Complete extracted text from each image")

if __name__ == "__main__":
    process_all_images()
, text):
                continue
            
            # Skip very short text (less than 3 chars)
            if len(text) < 3:
                continue
            
            # Skip common UI elements
            if text.lower() in ['edit', 'back', 'search', 'call', 'video']:
                continue
            
            # Skip checkmarks and single special characters
            if text in ['✓', '✔', '✓✓', '✔✔']:
                continue
            
            # This is likely the name/title
            potential_names.append(text)
            
            # Stop after finding first valid name (usually the top-most text)
            if len(potential_names) >= 1:
                break
    
    # Arabic messages
    arabic_pattern = r'[\u0600-\u06FF\s]+'
    arabic_texts = [t.strip() for t in re.findall(arabic_pattern, full_text) if len(t.strip()) > 5]
    
    return {
        'phone_numbers': phone_numbers,
        'names': potential_names,
        'timestamp': timestamp,
        'messages': arabic_texts,
        'all_text': full_text,
        'total_text_blocks': len(all_detections)
    }

# ===== Main Processing =====
def process_all_images():
    source_dir = SETTINGS['SOURCE_DIR']
    output_excel = SETTINGS['OUTPUT_EXCEL']
    
    if not os.path.exists(source_dir):
        print(f"Error: Directory '{source_dir}' not found!")
        return
    
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    image_files = [f for f in os.listdir(source_dir) if os.path.splitext(f.lower())[1] in image_extensions]
    
    if not image_files:
        print(f"No images found in '{source_dir}' directory!")
        return
    
    print(f"Found {len(image_files)} images to process")
    print("Initializing EasyOCR (this may take a moment)...")
    
    reader = easyocr.Reader(SETTINGS['LANGUAGES'], gpu=SETTINGS['USE_GPU'])
    
    phone_data, summary_data, all_text_data = [], [], []
    
    print("\nProcessing images...")
    print("-" * 70)
    
    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(source_dir, image_file)
        print(f"{idx}/{len(image_files)} Processing: {image_file}")
        try:
            info = extract_info_from_image(image_path, reader)
            
            if info['phone_numbers']:
                print(f"  ✓ Found {len(info['phone_numbers'])} phone numbers")
            else:
                print(f"  ⚠ No phone numbers found")
            
            # Phone sheet
            for phone in info['phone_numbers']:
                phone_data.append({
                    'Image_Name': image_file,
                    'Phone_Number': phone,
                    'Name': ', '.join(info['names']) if info['names'] else '',
                    'Timestamp': info['timestamp']
                })
            
            # Summary
            summary_data.append({
                'Image_Name': image_file,
                'Phone_Numbers_Count': len(info['phone_numbers']),
                'Names_Detected': ', '.join(info['names']) if info['names'] else 'None',
                'Timestamp': info['timestamp'] if info['timestamp'] else 'None',
                'Text_Blocks_Count': info['total_text_blocks']
            })
            
            # All text
            all_text_data.append({
                'Image_Name': image_file,
                'All_Extracted_Text': info['all_text'],
                'Arabic_Messages': ' | '.join(info['messages']) if info['messages'] else 'None'
            })
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            summary_data.append({
                'Image_Name': image_file,
                'Phone_Numbers_Count': 0,
                'Names_Detected': f'Error: {e}',
                'Timestamp': 'Error',
                'Text_Blocks_Count': 0
            })
    
    print("-" * 70)
    
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        if phone_data:
            pd.DataFrame(phone_data).to_excel(writer, sheet_name='Phone Numbers', index=False)
            unique_phones = list(set(d['Phone_Number'] for d in phone_data))
            pd.DataFrame({'Unique_Phone_Numbers': sorted(unique_phones)}).to_excel(writer, sheet_name='Unique Numbers', index=False)
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        pd.DataFrame(all_text_data).to_excel(writer, sheet_name='All Text', index=False)
    
    total_numbers = len(phone_data)
    unique_count = len(set(d['Phone_Number'] for d in phone_data)) if phone_data else 0
    
    print(f"\n✓ Processing complete!")
    print(f"  Total images processed: {len(image_files)}")
    print(f"  Total phone numbers found: {total_numbers}")
    print(f"  Unique phone numbers: {unique_count}")
    print(f"  Results saved to: {output_excel}")
    print(f"\nExcel sheets created:")
    print(f"  1. Phone Numbers - Phone numbers with name and timestamp")
    print(f"  2. Unique Numbers - Deduplicated phone numbers only")
    print(f"  3. Summary - Overview of each image")
    print(f"  4. All Text - Complete extracted text from each image")

if __name__ == "__main__":
    process_all_images()