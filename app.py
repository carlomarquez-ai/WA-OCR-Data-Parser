import re
import easyocr
import os
import pandas as pd

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

# ===== Phone Number Extraction =====
def extract_phone_numbers_global(text):
    """Extract phone numbers from various countries and formats."""
    phone_numbers = []

    # Patterns
    pattern1 = r'\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}'
    pattern2 = r'\b\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b'
    pattern3 = r'\b[\(]?0\d{1,3}[\)]?[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b'
    pattern4 = r'\b\d{10,15}\b'

    for pattern in [pattern1, pattern2, pattern3, pattern4]:
        matches = re.findall(pattern, text)
        phone_numbers.extend(matches)

    # Clean and normalize
    cleaned_numbers = []
    seen = set()
    for number in phone_numbers:
        cleaned = re.sub(r'[\s\-\(\)]', '', number)
        if len(cleaned) < 8 or len(cleaned) > 15:
            continue
        if cleaned == '0' * len(cleaned):
            continue
        # Normalize
        if not cleaned.startswith('+'):
            if cleaned.startswith('00'):
                cleaned = '+' + cleaned[2:]
            elif cleaned.startswith('0') and len(cleaned) == 10:
                cleaned = '+966' + cleaned[1:]
            elif cleaned.startswith('966'):
                cleaned = '+' + cleaned
            elif len(cleaned) >= 10:
                cleaned = '+' + cleaned
        if cleaned not in seen:
            seen.add(cleaned)
            cleaned_numbers.append(cleaned)

    return cleaned_numbers

# ===== Extract Info from Image =====
def extract_info_from_image(image_path, reader):
    result = reader.readtext(image_path)
    all_text = ' '.join([det[1] for det in result])
    phone_numbers = extract_phone_numbers_global(all_text)
    return {
        'phone_numbers': phone_numbers,
        'all_text': all_text
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

    phone_data, all_text_data = [], []

    print("\nProcessing images...")
    print("-" * 70)

    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(source_dir, image_file)
        print(f"{idx}/{len(image_files)} Processing: {image_file}")

        try:
            info = extract_info_from_image(image_path, reader)

            # Phone sheet
            for phone in info['phone_numbers']:
                phone_data.append({
                    'Image_Name': image_file,
                    'Phone_Number': phone
                })

            # All text
            all_text_data.append({
                'Image_Name': image_file,
                'All_Extracted_Text': info['all_text']
            })

        except Exception as e:
            print(f" ✗ Error: {e}")

    # Save results to Excel
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        if phone_data:
            pd.DataFrame(phone_data).to_excel(writer, sheet_name='Phone Numbers', index=False)
            unique_phones = list(set(d['Phone_Number'] for d in phone_data))
            pd.DataFrame({'Unique_Phone_Numbers': sorted(unique_phones)}).to_excel(writer, sheet_name='Unique Numbers', index=False)

        pd.DataFrame(all_text_data).to_excel(writer, sheet_name='All Text', index=False)

    total_numbers = len(phone_data) if phone_data else 0
    unique_count = len(set(d['Phone_Number'] for d in phone_data)) if phone_data else 0

    print(f"\n✓ Processing complete!")
    print(f" Total images processed: {len(image_files)}")
    print(f" Total phone numbers found: {total_numbers}")
    print(f" Unique phone numbers: {unique_count}")
    print(f" Results saved to: {output_excel}")
    print(f"\nExcel sheets created:")
    print(f" 1. Phone Numbers - Phone numbers extracted from each image")
    print(f" 2. Unique Numbers - Deduplicated phone numbers only")
    print(f" 3. All Text - Complete extracted text from each image")

if __name__ == "__main__":
    process_all_images()
