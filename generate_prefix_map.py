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
        self.acc_no_1 = None # For "Acc No."
        self.acc_no_2 = None # For "Accession No."

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
            elif 'Accession No.' in data:
                self.is_acc_no_label_2 = True
                self.is_acc_no_label_1 = False
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

def normalize_acc_no(acc_no):
    if not acc_no:
        return None
    # This regex will extract the numerical part of the accession number, including slashes and hyphens.
    match = re.search(r'[\d/-]+', acc_no)
    if match:
        return match.group(0).replace('-', '/')
    return None

def create_prefix_map_v6():
    prefix_map = {"*": "(Acc. No. missing) · "}
    file_list = glob.glob('docs/*.html')
    
    missing_acc_no_1_count = 0
    missing_acc_no_2_count = 0
    differences_count = 0
    total_files_processed = 0
    files_with_prefix = 0
    files_without_acc_no = []

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
                    
                    acc_no_1 = parser.acc_no_1
                    acc_no_2 = parser.acc_no_2

                    norm_acc_no_1 = normalize_acc_no(acc_no_1)
                    norm_acc_no_2 = normalize_acc_no(acc_no_2)

                    if not acc_no_1:
                        missing_acc_no_1_count += 1
                    if not acc_no_2:
                        missing_acc_no_2_count += 1

                    if acc_no_1 and acc_no_2 and norm_acc_no_1 != norm_acc_no_2:
                        differences_count += 1
                        diff_file.write(f"- {filename}: 'Acc No.': '{acc_no_1}' ('{norm_acc_no_1}'), 'Accession No.': '{acc_no_2}' ('{norm_acc_no_2}')\n")

                    final_acc_no = acc_no_2 if acc_no_2 else acc_no_1
                    
                    if final_acc_no:
                        prefix = f"{final_acc_no} · "
                        prefix_map[filename] = prefix
                        files_with_prefix += 1
                    else:
                        files_without_acc_no.append(filename)

            except Exception as e:
                print(f"Error processing file {filepath}: {e}")

        diff_file.write("\n\nFiles without any accession number:\n")
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
        f"Files still without any accession number: {total_files_processed - files_with_prefix}\n"
        f"\nA file named 'accession_number_problems.txt' has been created with the list of files with differing accession numbers and files without any accession number.\n"
    )
    with open('accession_number_problems.txt', 'a', encoding='utf-8') as diff_file:
        diff_file.write(summary)


if __name__ == '__main__':
    create_prefix_map_v6()
