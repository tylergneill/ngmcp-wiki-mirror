import os
import json
import glob
import re
from html.parser import HTMLParser
from tqdm import tqdm

class DualAccNoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_b = False
        self.is_acc_no_label_1 = False
        self.is_acc_no_label_2 = False
        self.is_place_of_deposit_label = False
        self.acc_no_1 = None
        self.acc_no_2 = None
        self.place_of_deposit = None

    def handle_starttag(self, tag, attrs):
        if tag == 'b':
            self.in_b = True

    def handle_endtag(self, tag):
        if tag == 'b':
            self.in_b = False

    def handle_data(self, data):
        if self.in_b:
            if 'Acc No.' in data:
                self.is_acc_no_label_1 = True
                self.is_acc_no_label_2 = False
                self.is_place_of_deposit_label = False
            elif 'Accession No.' in data:
                self.is_acc_no_label_2 = True
                self.is_acc_no_label_1 = False
                self.is_place_of_deposit_label = False
            elif 'Place of Deposit' in data:
                self.is_place_of_deposit_label = True
                self.is_acc_no_label_1 = False
                self.is_acc_no_label_2 = False
        elif self.is_acc_no_label_1:
            cleaned_data = data.strip()
            if cleaned_data and cleaned_data != ':':
                self.acc_no_1 = cleaned_data.lstrip(':').strip()
            self.is_acc_no_label_1 = False
        elif self.is_acc_no_label_2:
            cleaned_data = data.strip()
            if cleaned_data and cleaned_data != ':':
                self.acc_no_2 = cleaned_data.lstrip(':').strip()
            self.is_acc_no_label_2 = False
        elif self.is_place_of_deposit_label:
            cleaned_data = data.strip()
            if cleaned_data and cleaned_data != ':':
                self.place_of_deposit = cleaned_data.lstrip(':').strip()
            self.is_place_of_deposit_label = False

def normalize_acc_no_for_comparison(acc_no):
    if not acc_no:
        return None
    # Strip off word prefixes (like "Acc. No.", "Accession No.")
    cleaned_acc_no = re.sub(r'^(Acc\. No\.?|Accession No\.?)\s*[:-]?\s*', '', acc_no, flags=re.IGNORECASE).strip()

    # Phase 1: General Separator Normalization
    # Convert /, \, -, ., ,, and space to underscore
    cleaned_acc_no = re.sub(r'[\/\\., -]', '_', cleaned_acc_no)
    # Replace multiple underscores with a single underscore
    cleaned_acc_no = re.sub(r'_+', '_', cleaned_acc_no)
    # Remove leading/trailing underscores
    cleaned_acc_no = cleaned_acc_no.strip('_')

    # Phase 2: Numerical Portion Extraction
    # Keep only digits, underscores, and parentheses
    numerical_portion = re.sub(r'[^\d_()]', '', cleaned_acc_no).strip('_')

    return numerical_portion if numerical_portion else None

def create_prefix_map_v6():
    prefix_map = {"*": "(Acc. No. missing) · "}
    file_list = glob.glob('docs/*.html')
    
    missing_acc_no_1_count = 0
    missing_acc_no_2_count = 0
    differing_acc_numbers_list = [] # To store specific items
    files_without_any_acc_no = [] # To store specific items
    
    total_files_processed = 0
    files_with_prefix = 0

    with open('accession_number_problems.txt', 'w', encoding='utf-8') as diff_file:
        diff_file.write("Files with differing accession numbers:\n")

        for filepath in tqdm(file_list, desc="Processing files"):
            filename = os.path.basename(filepath)
            if filename == 'search.html' or filename == 'index.html':
                continue
            
            total_files_processed += 1
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    parser = DualAccNoParser()
                    parser.feed(content)
                    
                    raw_acc_no_1 = parser.acc_no_1
                    raw_acc_no_2 = parser.acc_no_2

                    # Update missing counts based on raw data
                    if not raw_acc_no_1:
                        missing_acc_no_1_count += 1
                    if not raw_acc_no_2:
                        missing_acc_no_2_count += 1

                    # Normalize for comparison
                    norm_1_for_comp = normalize_acc_no_for_comparison(raw_acc_no_1)
                    norm_2_for_comp = normalize_acc_no_for_comparison(raw_acc_no_2)

                    # Check for differing accession numbers (naive comparison)
                    if raw_acc_no_1 and raw_acc_no_2 and norm_1_for_comp != norm_2_for_comp:
                        differing_acc_numbers_list.append(f"- {filename}: 'Acc No.': '{raw_acc_no_1}' ('{norm_1_for_comp}'), 'Accession No.': '{raw_acc_no_2}' ('{norm_2_for_comp}')")

                    # Build the prefix string
                    prefix_parts = []
                    if raw_acc_no_1:
                        prefix_parts.append(raw_acc_no_1)
                        # If acc_no_2 exists and is different after normalization, add it too
                        if raw_acc_no_2 and norm_1_for_comp != norm_2_for_comp:
                            prefix_parts.append(raw_acc_no_2)
                    elif raw_acc_no_2: # Only if acc_no_1 is missing
                        prefix_parts.append(raw_acc_no_2)
                    
                    final_prefix_str = ""
                    if prefix_parts:
                        final_prefix_str = " · ".join(prefix_parts) + " · "
                    else:
                        final_prefix_str = "(Acc. No. missing) · "
                        files_without_any_acc_no.append(f"- {filename}")

                    prefix_map[filename] = final_prefix_str
                    if final_prefix_str != "(Acc. No. missing) · ":
                        files_with_prefix += 1

            except Exception as e:
                print(f"Error processing file {filepath}: {e}")

        # Write differing accession numbers to file
        for entry in differing_acc_numbers_list:
            diff_file.write(f"{entry}\n")

        diff_file.write("\n\nFiles still without any accession number:\n")
        for entry in files_without_any_acc_no:
            diff_file.write(f"{entry}\n")


    with open('docs/prefix-map.json', 'w', encoding='utf-8') as f:
        json.dump(prefix_map, f, ensure_ascii=False, indent=2)
        
    summary = (
        f"\n--- Summary ---\n"
        f"Total documents processed: {total_files_processed}\n"
        f"Files with a prefix: {files_with_prefix}\n"
        f"Files missing 'Acc No.': {missing_acc_no_1_count}\n"
        f"Files missing 'Accession No.': {missing_acc_no_2_count}\n"
        f"Files with differing accession numbers: {len(differing_acc_numbers_list)}\n"
        f"Files without any accession number: {len(files_without_any_acc_no)}\n"
    )
    with open('accession_number_problems.txt', 'a', encoding='utf-8') as diff_file:
        diff_file.write(summary)

if __name__ == '__main__':
    create_prefix_map_v6()
