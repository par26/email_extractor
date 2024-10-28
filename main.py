import csv
import re
import requests
from googlesearch import search
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import dns.resolver 


max_pages = 15


pageAvoid = ["xml", "zip", "doc", "ppt"]

def find_email_in_text(text):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, text)
    #removes duplicates 
    return list(set(emails))

def get_website_url(business_name):
    query = f"{business_name} official site"
    try:
        search_results = list(search(query, num=5, stop=5, pause=2))
        for url in search_results:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return url
            except requests.RequestException:
                continue
    except Exception as e:
        print(f"Error during Google search: {e}")
    return None

def clean_emails(emails):
    cleaned_emails = []
    for email in emails:
        if isinstance(email, list):
            cleaned_emails.extend(email)
        else:
            cleaned_emails.append(email)
    return cleaned_emails

def is_valid_email(email):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    if not re.fullmatch(email_regex, email):
        return False

    domain = email.split('@')[1]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return bool(records)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False

def urljoin(base_url, relative_url):
    base_parts = urlparse(base_url)
    relative_parts = urlparse(relative_url)

    if relative_parts.scheme:
        return relative_url

    path = relative_parts.path
    if not path.startswith('/'):
        base_path = base_parts.path.rsplit('/', 1)[0]
        path = f"{base_path}/{path}"

    
    full_url_parts = (
        base_parts.scheme,
        base_parts.netloc,
        path,
        relative_parts.params,
        relative_parts.query,
        relative_parts.fragment
    )
    return urlunparse(full_url_parts)

def scrape_email_from_website(url):
    try:
        visited = set()
        to_visit = [url]
        all_content = ""

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            print(f"Crawling: {current_url}")
            try:
                response = requests.get(current_url)
                visited.add(current_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    all_content += response.text

                    # Find all links on the page
                    for link in soup.find_all('a', href=True):
                        full_url = urljoin(url, link['href'])
                        if (full_url.startswith(url)
                            and full_url not in visited 
                            and check_url_valid(full_url)):
                                to_visit.append(link['href'])
            except requests.RequestException:
                continue  # Skip to the next URL if there's a problem with the request

        emails = find_email_in_text(all_content)
        if emails:

            valid_emails = [email for email in emails if is_valid_email(email)]
            return valid_emails

        return []

    except requests.RequestException:
        return []


def check_url_valid(url):
    for page in pageAvoid:
        if page in url:
            return False

def main():
    with open('businesses.csv', 'r') as infile:
        reader = csv.reader(infile)
        businesses = [row[0] for row in reader]

    business_emails = {}

    for business in businesses:
        print(f"Processing: {business}")
        url = get_website_url(business)
        if url:
            emails = scrape_email_from_website(url)
            if emails:
                business_emails[business] = emails
            else:
                business_emails[business] = ['No email found']
        else:
            business_emails[business] = ['No URL found']

    with open('emails.csv', 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['Business Name', 'Email'])
        for business, emails in business_emails.items():
            for email in emails:
                writer.writerow([business, email])

    print("Scraping completed. Check emails.csv for results.")

if __name__ == "__main__":
    main()

