import re
import easyocr
import os
import pandas as pd
from datetime import datetime

def extract_phone_numbers_easy(image_path, reader):
    # Perform OCR
    result = reader.readtext(image_path)
    
    # Extract all text
    all_text = []
    for detection in result:
        text = detection[1]  # detection[1] contains the text
        all_text.append(text)
    
    # Combine all text
    full_text = ' '.join(all_text)
    
    # Pattern to match phone numbers
    phone_patterns = [
        r'\+966\s*\d{1,2}\s*\d{3}\s*\d{4}',  # +966 XX XXX XXXX
        r'\+966\d{9}',                        # +966XXXXXXXXX
        r'966\s*\d{1,2}\s*\d{3}\s*\d{4}',    # 966 XX XXX XXXX
        r'05\d{8}',                           # 05XXXXXXXX
    ]
    
    phone_numbers = []
    
    # Search for all patterns
    for pattern in phone_patterns:
        matches = re.findall(pattern, full_text)
        phone_numbers.extend(matches)
    
    # Clean up phone numbers
    cleaned_numbers = []
    for number in phone_numbers:
        # Remove all spaces
        cleaned = number.replace(' ', '')
        # Ensure it starts with +
        if not cleaned.startswith('+'):
            if cleaned.startswith('966'):
                cleaned = '+' + cleaned
            elif cleaned.startswith('05'):
                cleaned = '+966' + cleaned[1:]
        cleaned_numbers.append(cleaned)
    
    # Return unique phone numbers
    return list(set(cleaned_numbers))


def process_all_images(source_dir='source_image', output_excel='phone_numbers.xlsx'):
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
    
    # Store all results
    all_data = []
    
    print("\nProcessing images...")
    print("-" * 70)
    
    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(source_dir, image_file)
        print(f"{idx}/{len(image_files)} Processing: {image_file}")
        
        try:
            phone_numbers = extract_phone_numbers_easy(image_path, reader)
            
            if phone_numbers:
                print(f"  ✓ Found {len(phone_numbers)} phone numbers")
                for number in phone_numbers:
                    all_data.append({
                        'Image_Name': image_file,
                        'Phone_Number': number
                    })
            else:
                print(f"  ⚠ No phone numbers found")
                all_data.append({
                    'Image_Name': image_file,
                    'Phone_Number': 'No numbers found'
                })
        except Exception as e:
            print(f"  ✗ Error processing image: {str(e)}")
            all_data.append({
                'Image_Name': image_file,
                'Phone_Number': f'Error: {str(e)}'
            })
    
    print("-" * 70)
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Save to Excel
    df.to_excel(output_excel, index=False, engine='openpyxl')
    
    # Print summary
    total_numbers = len([d for d in all_data if d['Phone_Number'].startswith('+')])
    print(f"\n✓ Processing complete!")
    print(f"  Total images processed: {len(image_files)}")
    print(f"  Total phone numbers found: {total_numbers}")
    print(f"  Results saved to: {output_excel}")
    
    return df


def create_summary_excel(source_dir='source_image', output_excel='phone_numbers_summary.xlsx'):
    """
    Create Excel with both detailed and summary sheets.
    
    Args:
        source_dir: Directory containing images
        output_excel: Output Excel file name
    """
    # Check if directory exists
    if not os.path.exists(source_dir):
        print(f"Error: Directory '{source_dir}' not found!")
        return
    
    # Get all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    image_files = [f for f in os.listdir(source_dir) 
                    if os.path.splitext(f.lower())[1] in image_extensions]
    
    if not image_files:
        print(f"No images found in '{source_dir}' directory!")
        return
    
    print(f"Found {len(image_files)} images to process")
    print("Initializing EasyOCR...")
    
    reader = easyocr.Reader(['en', 'ar'], gpu=False)
    
    detailed_data = []
    summary_data = []
    
    print("\nProcessing images...")
    print("-" * 70)
    
    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(source_dir, image_file)
        print(f"{idx}/{len(image_files)} Processing: {image_file}")
        
        try:
            phone_numbers = extract_phone_numbers_easy(image_path, reader)
            
            if phone_numbers:
                print(f"  ✓ Found {len(phone_numbers)} phone numbers")
                for number in phone_numbers:
                    detailed_data.append({
                        'Image_Name': image_file,
                        'Phone_Number': number
                    })
                
                summary_data.append({
                    'Image_Name': image_file,
                    'Numbers_Found': len(phone_numbers),
                    'Status': 'Success'
                })
            else:
                print(f"  ⚠ No phone numbers found")
                summary_data.append({
                    'Image_Name': image_file,
                    'Numbers_Found': 0,
                    'Status': 'No numbers found'
                })
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            summary_data.append({
                'Image_Name': image_file,
                'Numbers_Found': 0,
                'Status': f'Error: {str(e)}'
            })
    
    print("-" * 70)
    
    # Create Excel with multiple sheets
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        # Detailed sheet
        df_detailed = pd.DataFrame(detailed_data)
        df_detailed.to_excel(writer, sheet_name='All Phone Numbers', index=False)
        
        # Summary sheet
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Unique numbers sheet
        if detailed_data:
            unique_numbers = list(set([d['Phone_Number'] for d in detailed_data]))
            df_unique = pd.DataFrame({'Unique_Phone_Numbers': sorted(unique_numbers)})
            df_unique.to_excel(writer, sheet_name='Unique Numbers', index=False)
    
    # Print summary
    total_numbers = len(detailed_data)
    unique_count = len(set([d['Phone_Number'] for d in detailed_data])) if detailed_data else 0
    
    print(f"\n✓ Processing complete!")
    print(f"  Total images processed: {len(image_files)}")
    print(f"  Total phone numbers found: {total_numbers}")
    print(f"  Unique phone numbers: {unique_count}")
    print(f"  Results saved to: {output_excel}")

if __name__ == "__main__":
    create_summary_excel('source_image', 'phone_numbers_complete.xlsx')
