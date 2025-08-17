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

def extract_number(acc_no):
    if not acc_no:
        return None
    match = re.search(r'[\d/.-]+', acc_no)
    if match:
        return match.group(0).replace('-', '/')
    return None

def normalize_acc_no(acc_no):
    if not acc_no:
        return None, False
    
    original_acc_no_upper = acc_no.upper()
    nak_present = "NAK" in original_acc_no_upper

    # Clean up the accession number string
    cleaned_acc_no = acc_no.strip()
    # Remove common prefixes/suffixes that are not part of the actual number
    cleaned_acc_no = re.sub(r'^(Acc\.? No\.?|Accession No\.?)\s*[:-]?\s*', '', cleaned_acc_no, flags=re.IGNORECASE).strip()
    cleaned_acc_no = re.sub(r'\s*\(.*?\)$', '', cleaned_acc_no).strip() # Remove anything in parentheses at the end
    
    # If NAK was present in the original, remove it from the cleaned string for now,
    # as we'll handle prefixing in the main logic.
    if nak_present:
        cleaned_acc_no = cleaned_acc_no.replace('NAK', '', 1).replace('nak', '', 1).strip()

    # Extract the number part if it exists, otherwise use the cleaned string
    number_part = extract_number(cleaned_acc_no)
    
    return number_part if number_part else (cleaned_acc_no if cleaned_acc_no else None), nak_present

def create_prefix_map_v6():
    prefix_map = {"*": "(Acc. No. missing) · "}
    file_list = glob.glob('docs/*.html')
    
    missing_acc_no_1_count = 0
    missing_acc_no_2_count = 0
    differences_count = 0
    total_files_processed = 0
    files_with_prefix = 0
    files_without_acc_no = []
    nak_supplied_files = []

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
                    if 'E 423-32 Kubjikāmantra' in content:
                        breakpoint()
                    parser = DualAccNoParser()
                    parser.feed(content)
                    
                    acc_no_1 = parser.acc_no_1
                    acc_no_2 = parser.acc_no_2
                    place_of_deposit = parser.place_of_deposit

                    # Normalize individual accession numbers first
                    norm_acc_no_1, nak_in_1_original = normalize_acc_no(acc_no_1)
                    norm_acc_no_2, nak_in_2_original = normalize_acc_no(acc_no_2)

                    final_acc_no = None
                    nak_was_added_by_system = False

                    if nak_in_1_original: # Rule 1: if 'NAK' in acc_no_1
                        if norm_acc_no_2:
                            final_acc_no = "NAK " + norm_acc_no_2
                        else:
                            final_acc_no = "NAK " + (norm_acc_no_1 if norm_acc_no_1 else "")
                        nak_was_added_by_system = True
                    elif norm_acc_no_2: # Rule 2: otherwise, look in the "Place of Deposit" and prefix to acc_no_2
                        if place_of_deposit:
                            final_acc_no = f"{place_of_deposit} {norm_acc_no_2}"
                        else:
                            final_acc_no = norm_acc_no_2
                    elif norm_acc_no_1: # Rule 3: if using acc_no_1 bc acc_no_2 is not available, use as-is
                        final_acc_no = norm_acc_no_1

                    if final_acc_no and nak_was_added_by_system:
                        nak_supplied_files.append(f"- {filename}: '{acc_no_2 if acc_no_2 else acc_no_1}' -> '{final_acc_no}'")

                    if not acc_no_1:
                        missing_acc_no_1_count += 1
                    if not acc_no_2:
                        missing_acc_no_2_count += 1

                    # The difference check should use the normalized numbers without the NAK/Place of Deposit prefixing
                    # to compare the core accession numbers.
                    if acc_no_1 and acc_no_2 and norm_acc_no_1 != norm_acc_no_2:
                        differences_count += 1
                        diff_file.write(f"- {filename}: 'Acc No.': '{acc_no_1}' ('{norm_acc_no_1}'), 'Accession No.': '{acc_no_2}' ('{norm_acc_no_2}')\n")

                    if final_acc_no:
                        prefix = f"{final_acc_no} · "
                        prefix_map[filename] = prefix
                        files_with_prefix += 1
                    else:
                        files_without_acc_no.append(filename)

            except Exception as e:
                print(f"Error processing file {filepath}: {e}")

        diff_file.write("\n\nFiles where 'NAK' was supplied:\n")
        for entry in nak_supplied_files:
            diff_file.write(f"{entry}\n")

        diff_file.write("\n\nFiles still without any accession number:\n")
        for filename in files_without_acc_no:
            diff_file.write(f"- {filename}\n")


    with open('docs/prefix-map.json', 'w', encoding='utf-8') as f:
        json.dump(prefix_map, f, ensure_ascii=False, indent=2)
        
    summary = (
        f"\n--- Summary ---\n"
        f"Total documents processed: {total_files_processed}\n"
        f"Files with a prefix: {files_with_prefix}\n"
        f"Files missing 'Acc No.': {missing_acc_no_1_count}\n"
        f"Files missing 'Accession No.': {missing_acc_no_2_count}\n"
        f"Files with differing accession numbers: {differences_count}\n"
        f"Files where 'NAK' was supplied by system: {len(nak_supplied_files)}\n"
        f"Files still without any accession number: {total_files_processed - files_with_prefix}\n"
        f"\nA file named 'accession_number_problems.txt' has been created with the list of files with differing accession numbers and files without any accession number.\n"
    )
    with open('accession_number_problems.txt', 'a', encoding='utf-8') as diff_file:
        diff_file.write(summary)

if __name__ == '__main__':
    create_prefix_map_v6()