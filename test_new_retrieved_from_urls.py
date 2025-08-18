import argparse
import requests
import webbrowser
from tqdm import tqdm
import os

def test_urls(url_file, check_200, open_browser):
    if not os.path.exists(url_file):
        print(f"Error: URL file '{url_file}' not found.")
        return

    with open(url_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print(f"No URLs found in '{url_file}'.")
        return

    print(f"Processing {len(urls)} URLs from '{url_file}'...")

    for url in tqdm(urls[::15], desc="Testing URLs"):  # every 15th
        if check_200:
            try:
                response = requests.get(url, timeout=10) # 10-second timeout
                if response.status_code == 200:
                    tqdm.write(f"SUCCESS (200 OK): {url}")
                else:
                    tqdm.write(f"FAILURE ({response.status_code}): {url}")
            except requests.exceptions.RequestException as e:
                tqdm.write(f"ERROR (Request Failed): {url} - {e}")
        
        if open_browser:
            tqdm.write(f"Opening in browser: {url}")
            webbrowser.open(url)

def main():
    parser = argparse.ArgumentParser(description="Test URLs from a file.")
    parser.add_argument("url_file", help="Path to the file containing URLs (one per line).")
    parser.add_argument("--check-200", action="store_true", 
                        help="Check if URLs return a 200 OK response.")
    parser.add_argument("--open-browser", action="store_true",
                        help="Open URLs in the default web browser.")
    
    args = parser.parse_args()

    if not args.check_200 and not args.open_browser:
        print("Please specify at least one action: --check-200 or --open-browser.")
        parser.print_help()
        return

    test_urls(args.url_file, args.check_200, args.open_browser)

if __name__ == "__main__":
    main()
