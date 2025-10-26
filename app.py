import re
import easyocr
import os
import pandas as pd
from datetime import datetime

def extract_info_from_image(image_path, reader):
    # Perform OCR
    result = reader.readtext(image_path)
    
    # Extract all text with positions
    all_detections = []
    all_text = []
    
    for detection in result:
        bbox = detection[0]
        text = detection[1]
        confidence = detection[2]
        
        all_detections.append({
            'text': text,
            'confidence': confidence,
            'y_position': bbox[0][1]
        })
        all_text.append(text)
    
    # Sort by Y position (top to bottom)
    all_detections.sort(key=lambda x: x['y_position'])
    
    # Combine all text
    full_text = ' '.join(all_text)
    
    # Extract phone numbers
    phone_patterns = [
        r'\+966\s*\d{1,2}\s*\d{3}\s*\d{4}',  # +966 XX XXX XXXX
        r'\+966\d{9}',                        # +966XXXXXXXXX
        r'966\s*\d{1,2}\s*\d{3}\s*\d{4}',    # 966 XX XXX XXXX
        r'05\d{8}',                           # 05XXXXXXXX
    ]
    
    phone_numbers = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, full_text)
        phone_numbers.extend(matches)
    
    # Clean up phone numbers
    cleaned_numbers = []
    for number in phone_numbers:
        cleaned = number.replace(' ', '')
        if not cleaned.startswith('+'):
            if cleaned.startswith('966'):
                cleaned = '+' + cleaned
            elif cleaned.startswith('05'):
                cleaned = '+966' + cleaned[1:]
        cleaned_numbers.append(cleaned)
    
    phone_numbers = list(set(cleaned_numbers))
    
    # Extract timestamps (day names, time patterns)
    day_pattern = r'Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|الأحد|الإثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت'
    time_pattern = r'\d{1,2}:\d{2}'
    arabic_time_pattern = r'اخر \d+ ساعه'
    
    day_match = re.search(day_pattern, full_text)
    time_match = re.search(time_pattern, full_text)
    arabic_time_match = re.search(arabic_time_pattern, full_text)
    
    # Combine day and time
    timestamp = ''
    if day_match and time_match:
        timestamp = f"{day_match.group()} {time_match.group()}"
    elif day_match:
        timestamp = day_match.group()
    elif time_match:
        timestamp = time_match.group()
    elif arabic_time_match:
        timestamp = arabic_time_match.group()
    
    # Extract potential names from top banner only (first 10-15% of image)
    # Get image height to determine top banner area
    if all_detections:
        max_y = max(det['y_position'] for det in all_detections)
        top_banner_threshold = max_y * 0.15  # Top 15% of image
        
        potential_names = []
        
        for det in all_detections:
            # Only check text in top banner area
            if det['y_position'] > top_banner_threshold:
                continue
                
            text = det['text'].strip()
            
            # Skip if it's a phone number
            if any(re.search(pattern, text) for pattern in phone_patterns):
                continue
            
            # Skip timestamps
            if re.search(r'Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday', text):
                continue
            if re.search(r'\d{1,2}:\d{2}', text):
                continue
            if re.search(r'الأحد|الإثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت', text):
                continue
            
            # Skip very short text and common UI elements
            if len(text) <= 2:
                continue
            if text.lower() in ['edit', 'back', 'search']:
                continue
            
            # Add as potential name
            potential_names.append(text)
    else:
        potential_names = []
    
    # Extract messages (Arabic text that looks like messages)
    messages = []
    message_pattern = r'الله محييكم كلمتنا وعندك اهتمام اذا و'
    if re.search(message_pattern, full_text):
        messages.append(message_pattern)
    
    # Get all Arabic text (likely messages)
    arabic_pattern = r'[\u0600-\u06FF\s]+'
    arabic_texts = re.findall(arabic_pattern, full_text)
    arabic_texts = [text.strip() for text in arabic_texts if len(text.strip()) > 5]
    
    return {
        'phone_numbers': phone_numbers,
        'names': potential_names,
        'timestamp': timestamp,
        'messages': arabic_texts,
        'all_text': full_text,
        'total_text_blocks': len(all_detections)
    }


def process_all_images(source_dir='source_image', output_excel='result.xlsx'):
    
    # Check if directory exists
    if not os.path.exists(source_dir):
        print(f"Error: Directory '{source_dir}' not found!")
        print(f"Please create the directory and add your images.")
        return
    
    # Get all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    image_files = [f for f in os.listdir(source_dir) 
                    if os.path.splitext(f.lower())[1] in image_extensions]
    
    if not image_files:
        print(f"No images found in '{source_dir}' directory!")
        return
    
    print(f"Found {len(image_files)} images to process")
    print("Initializing EasyOCR (this may take a moment)...")
    
    # Initialize EasyOCR reader once
    reader = easyocr.Reader(['en', 'ar'], gpu=False)
    
    # Store results for different sheets
    phone_data = []
    summary_data = []
    all_text_data = []
    
    print("\nProcessing images...")
    print("-" * 70)
    
    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(source_dir, image_file)
        print(f"{idx}/{len(image_files)} Processing: {image_file}")
        
        try:
            info = extract_info_from_image(image_path, reader)
            
            # Add to phone numbers sheet
            if info['phone_numbers']:
                print(f"  ✓ Found {len(info['phone_numbers'])} phone numbers")
                for phone in info['phone_numbers']:
                    phone_data.append({
                        'Image_Name': image_file,
                        'Phone_Number': phone,
                        'Name': ', '.join(info['names']) if info['names'] else '',
                        'Timestamp': info['timestamp']
                    })
            else:
                print(f"  ⚠ No phone numbers found")
            
            # Add to summary sheet
            summary_data.append({
                'Image_Name': image_file,
                'Phone_Numbers_Count': len(info['phone_numbers']),
                'Names_Detected': ', '.join(info['names']) if info['names'] else 'None',
                'Timestamp': info['timestamp'] if info['timestamp'] else 'None',
                'Text_Blocks_Count': info['total_text_blocks']
            })
            
            # Add to all text sheet
            all_text_data.append({
                'Image_Name': image_file,
                'All_Extracted_Text': info['all_text'],
                'Arabic_Messages': ' | '.join(info['messages']) if info['messages'] else 'None'
            })
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            summary_data.append({
                'Image_Name': image_file,
                'Phone_Numbers_Count': 0,
                'Names_Detected': f'Error: {str(e)}',
                'Timestamp': 'Error',
                'Text_Blocks_Count': 0
            })
    
    print("-" * 70)
    
    # Create Excel with multiple sheets
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        # Phone numbers with context
        if phone_data:
            df_phones = pd.DataFrame(phone_data)
            df_phones.to_excel(writer, sheet_name='Phone Numbers', index=False)
            
            # Unique phone numbers
            unique_phones = list(set([d['Phone_Number'] for d in phone_data]))
            df_unique = pd.DataFrame({'Unique_Phone_Numbers': sorted(unique_phones)})
            df_unique.to_excel(writer, sheet_name='Unique Numbers', index=False)
        
        # Summary
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # All extracted text
        df_text = pd.DataFrame(all_text_data)
        df_text.to_excel(writer, sheet_name='All Text', index=False)
    
    # Print summary
    total_numbers = len(phone_data)
    unique_count = len(set([d['Phone_Number'] for d in phone_data])) if phone_data else 0
    
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
    process_all_images('source_image', 'result.xlsx')