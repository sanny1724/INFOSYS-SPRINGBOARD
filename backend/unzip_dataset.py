import zipfile
import os
import glob

# Find any zip file in the current directory
zip_files = glob.glob("*.zip")

if not zip_files:
    print("No zip files found in the current directory.")
    print("Please place your dataset zip file in the 'backend' folder.")
else:
    zip_path = zip_files[0] # Use the first one found
    extract_to = "dataset"
    
    print(f"Found zip file: {zip_path}")
    print(f"Extracting to {extract_to}...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print("Extraction complete!")
        
        # Check for nested data.yaml and move if necessary
        # (Simple check, user might need to adjust manually if structure is weird)
        if os.path.exists(os.path.join(extract_to, "data.yaml")):
            print("Found data.yaml in dataset root.")
            
    except Exception as e:
        print(f"Error extracting zip: {e}")
