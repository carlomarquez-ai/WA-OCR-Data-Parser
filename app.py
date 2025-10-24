import re
import easyocr

def extract_phone_numbers_easy(image_path):
    """
    Extract phone numbers from an image using EasyOCR.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        list: List of unique phone numbers found
    """
    # Initialize EasyOCR reader
    # ['en', 'ar'] for English and Arabic
    # gpu=True for faster processing (if you have CUDA-enabled GPU)
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en', 'ar'], gpu=False)
    
    # Perform OCR
    print("Processing image...")
    result = reader.readtext(image_path)
    
    # Extract all text
    all_text = []
    for detection in result:
        text = detection[1]  # detection[1] contains the text
        all_text.append(text)
    
    # Combine all text
    full_text = ' '.join(all_text)
    
    print(f"Extracted text: {full_text[:200]}...")  # Show first 200 chars
    
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


def extract_and_save_easy(image_path, output_file='phone_numbers.txt'):
    """
    Extract phone numbers using EasyOCR and save to file.
    
    Args:
        image_path: Path to the image file
        output_file: Path to output text file
    """
    phone_numbers = extract_phone_numbers_easy(image_path)
    
    # Print to console
    print(f"\nFound {len(phone_numbers)} unique phone numbers:")
    for number in sorted(phone_numbers):
        print(number)
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        for number in sorted(phone_numbers):
            f.write(number + '\n')
    
    print(f"\nPhone numbers saved to {output_file}")
    return phone_numbers


def extract_with_details(image_path):
    """
    Extract phone numbers and show OCR details for debugging.
    """
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en', 'ar'], gpu=False)
    
    print("Processing image...")
    result = reader.readtext(image_path)
    
    print("\nOCR Results:")
    print("-" * 70)
    
    for idx, detection in enumerate(result):
        bbox = detection[0]  # Bounding box coordinates
        text = detection[1]   # Detected text
        confidence = detection[2]  # Confidence score
        print(f"{idx+1}. Text: {text:30} | Confidence: {confidence:.3f}")
    
    print("-" * 70)
    
    phone_numbers = extract_phone_numbers_easy(image_path)
    print(f"\nExtracted phone numbers: {phone_numbers}")
    
    return phone_numbers


def batch_extract(image_paths):
    """
    Extract phone numbers from multiple images.
    
    Args:
        image_paths: List of image file paths
        
    Returns:
        dict: Dictionary mapping image paths to extracted phone numbers
    """
    # Initialize reader once for all images
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en', 'ar'], gpu=False)
    
    results = {}
    
    for image_path in image_paths:
        print(f"\nProcessing {image_path}...")
        result = reader.readtext(image_path)
        
        all_text = ' '.join([detection[1] for detection in result])
        
        phone_patterns = [
            r'\+966\s*\d{1,2}\s*\d{3}\s*\d{4}',
            r'\+966\d{9}',
            r'966\s*\d{1,2}\s*\d{3}\s*\d{4}',
            r'05\d{8}',
        ]
        
        phone_numbers = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, all_text)
            phone_numbers.extend(matches)
        
        cleaned_numbers = []
        for number in phone_numbers:
            cleaned = number.replace(' ', '')
            if not cleaned.startswith('+'):
                if cleaned.startswith('966'):
                    cleaned = '+' + cleaned
                elif cleaned.startswith('05'):
                    cleaned = '+966' + cleaned[1:]
            cleaned_numbers.append(cleaned)
        
        results[image_path] = list(set(cleaned_numbers))
        print(f"Found {len(results[image_path])} phone numbers")
    
    return results


# Example usage
if __name__ == "__main__":
    # Replace with your image path
    image_path = "1.png"
    
    # Method 1: Simple extraction
    numbers = extract_phone_numbers_easy(image_path)
    print(numbers)
    
    # Method 2: Extract and save
    # numbers = extract_and_save_easy(image_path)
    
    # Method 3: With debugging details
    # numbers = extract_with_details(image_path)
    
    # Method 4: Batch processing multiple images
    # image_list = ["image1.png", "image2.png", "image3.png"]
    # all_numbers = batch_extract(image_list)
