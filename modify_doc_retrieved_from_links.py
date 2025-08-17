import re
import urllib.parse
import os
import fnmatch

def find_html_files(directory):
    html_files = []
    for root, _, files in os.walk(directory):
        for filename in fnmatch.filter(files, '*.html'):
            html_files.append(os.path.join(root, filename))
    return html_files

# New constant for the output file
OUTPUT_URL_FILE = "new_retrieved_from_urls.txt"

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex to find the <a> tag within the "Retrieved from" line directly
        # This pattern assumes "Retrieved from" is unique and directly precedes the <a> tag.
        # Group 1: "Retrieved from "
        # Group 2: The part before href=" (e.g., <a dir="ltr" )
        # Group 3: The full old URL from the href attribute
        # Group 4: The value of the 'title' parameter (the filename part)
        # Group 5: The part between the href value and the link text (e.g., ">
        # Group 6: The visible link text (which is the old URL)
        # Group 7: The closing </a> tag
        # Group 8: The rest of the div content after </a>"
        pattern = r'(Retrieved from ")(.*href=")(http://ngmcp.fdm.uni-hamburg.de/mediawiki/index.php\?title=([^&\"]+)&amp;oldid=[^\"]+)(">)(.*)(</a>")(.*\s*</div>)'

        match = re.search(pattern, content, re.DOTALL)

        if match:
            retrieved_from_prefix = match.group(1)
            pre_href = match.group(2)
            old_full_url = match.group(3)
            encoded_filename_part = match.group(4)
            post_href_pre_text = match.group(5)
            old_link_text = match.group(6)
            post_a_tag_suffix = match.group(7)
            div_suffix = match.group(8)


            # Decode the filename part once
            decoded_filename = urllib.parse.unquote(encoded_filename_part)

            # Double URL-encode the decoded filename
            double_encoded_filename = urllib.parse.quote(urllib.parse.quote(decoded_filename, safe=''), safe='')

            # Construct the new URL
            new_url = f"https://www-archiv.fdm.uni-hamburg.de/ngmcp/{double_encoded_filename}.html"

            # Construct the new <a> tag content
            new_a_tag_content = f"{pre_href}{new_url}{post_href_pre_text}{new_url}{post_a_tag_suffix}"

            # Construct the full new line
            new_line = f"{retrieved_from_prefix}{new_a_tag_content}{div_suffix}"

            new_content = content.replace(match.group(0), new_line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated: {file_path}")

            # Append the new URL to the output file
            with open(OUTPUT_URL_FILE, 'a', encoding='utf-8') as outfile:
                outfile.write(new_url + '\n')

        # else:
        #     print(f"No matching link found in: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    docs_directory = "/Users/tyler/Git/ngmcp-wiki-mirror/docs" # Assuming this is the base directory for docs
    html_files_to_process = find_html_files(docs_directory)
    
    # Clear the output file before starting a new run
    if os.path.exists(OUTPUT_URL_FILE):
        os.remove(OUTPUT_URL_FILE)

    print(f"Found {len(html_files_to_process)} HTML files to process.")
    
    for file_path in html_files_to_process:
        process_file(file_path)
    print("Script finished processing files.")
