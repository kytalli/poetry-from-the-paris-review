import os
import logging
import base64
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import attr
import json
from datetime import datetime
from poem_utils import Poem

# Set up logging to file
log_filename = 'gmail_threads.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename,
    filemode='w'  # 'w' for write mode, 'a' for append mode
)

def get_message_content(message):
    """Extract and decode the message content, subject, and fetch the sent date."""
    subject = None
    sent_date = None
    
    # Find the subject and date in the headers
    for header in message['payload']['headers']:
        if header['name'].lower() == 'subject':
            subject = header['value']
        elif header['name'].lower() == 'date':
            sent_date = header['value']

    message_content = ""
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                logging.debug(f"Found text/plain part in message ID: {message['id']}")
                message_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
            elif part['mimeType'] == 'text/html':
                logging.debug(f"Found text/html part in message ID: {message['id']}")
                html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                message_content = extract_text_from_html(html_content)
                break
            elif part['mimeType'] == 'multipart/alternative':
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain':
                        logging.debug(f"Found text/plain subpart in multipart/alternative message ID: {message['id']}")
                        message_content = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
                        break
                    elif subpart['mimeType'] == 'text/html':
                        logging.debug(f"Found text/html subpart in multipart/alternative message ID: {message['id']}")
                        html_content = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
                        message_content = extract_text_from_html(html_content)
                        break
    else:
        if 'body' in message['payload'] and 'data' in message['payload']['body']:
            message_content = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')

    
    return message_content, subject, sent_date

def parse_subject(subject):
    """
    Parses the subject line to extract the poem title and author's name.
    Tries a primary pattern first and falls back to a secondary pattern if no match is found.

    Args:
        subject (str): The subject line containing the poem title and author.

    Returns:
        tuple: Returns a tuple containing the poem title and author's name.
    """
    # Primary pattern
    primary_pattern = r'“(.+?),”\s*(.+)'
    match = re.search(primary_pattern, subject)

    if match:
        poem_title = match.group(1)
        author_name = match.group(2)
        return poem_title, author_name
    else:
        # Fallback pattern for nested quotes or different formats
        fallback_pattern = r'“(from ‘(.+?),’)”\s*(.+)'
        match = re.search(fallback_pattern, subject)
        if match:
            poem_title = match.group(1)  # This captures the title inside the nested quotes
            author_name = match.group(3)
            poem_title = poem_title.replace("‘", '“').replace("’", '”').replace(",", "")
            return poem_title, author_name
        else:
            return None, None
    
def extract_poem_details(email_body, poem_title):
    """
    Extracts poem body and issue details from the provided email body text.

    Args:
        email_body (str): The body of the email containing the poem and other information.
        poem_title (str): The title of the poem used to locate the poem in the email body.

    Returns:
        tuple: A tuple containing the poem body and the issue information.
    """
    # Pattern to find the poem body and the issue details
    # This pattern assumes the poem starts immediately after its title and ends before "From issue"
    poem_body_pattern = re.compile(re.escape(poem_title) + r'(.*?)From issue', re.DOTALL)
    issue_pattern = re.compile(r'(From issue no. \d+.*?\s*\([^)]*\))', re.DOTALL)

    # Search for patterns in the email body
    poem_body_match = poem_body_pattern.search(email_body)
    issue_match = issue_pattern.search(email_body)

    poem_body = poem_body_match.group(1).strip() if poem_body_match else None
    poem_issue = issue_match.group(1).strip() if issue_match else None

    return poem_body, poem_issue


def save_message_to_file(message, directory, thread_id, subject):
    """
    Saves the content of a single message into a text file within a specified directory.

    Args:
        message (dict): Message dictionary containing message details.
        directory (str): Directory path where the file will be saved.
        thread_id (str): ID of the thread to which the message belongs.
        message_id (str): ID of the message.

    Returns:
        None
    """
    if not os.path.exists(directory):
        os.makedirs(directory)  # Create the directory if it does not exist

    file_path = os.path.join(directory, f'message_{thread_id}.txt')
    with open(file_path, 'w', encoding='utf-8') as file:
        message_content, subject = get_message_content(message)  # Assuming this function extracts the content
        # Write the content to the file, ensuring proper handling of escape characters
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            # Write the subject and content to file, handling new lines properly
            file.write(f"Subject: {subject}\n\n")
            file.write(message_content)  # Directly write the message content
    except Exception as e:
        print(f"Error writing to file {file_path}: {str(e)}")

    print(f"Message saved to file: {file_path}")


def extract_text_from_html(html_content):
    """Extract text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()

def setup_gmail_client():
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    logging.debug("Starting setup_gmail_client")
    if os.path.exists('token.json'):
        logging.debug("token.json found")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        logging.error("token.json not found")
        return None

    try:
        service = build("gmail", "v1", credentials=creds)
        logging.debug("Gmail API client built successfully")
        return service
    except Exception as e:
        logging.error(f"Failed to build Gmail API client: {str(e)}")
        return None

def fetch_threads(service, query):
    logging.debug(f"Fetching threads with query: {query}")
    threads = []
    page_token = None
    try:
        while True:
            response = service.users().threads().list(userId="me", pageToken=page_token, q=query).execute()
            fetched_threads = response.get("threads", [])
            threads.extend(fetched_threads)
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        logging.debug("Fetched threads successfully")
        return threads
    except Exception as e:
        logging.error(f"Error fetching threads: {str(e)}")
        return []
    
def process_messages(service, threads):
    poems = []
    for thread in threads:
        logging.debug(f"Processing thread ID: {thread['id']}")
        tdata = service.users().threads().get(userId="me", id=thread["id"]).execute()
        for message in tdata["messages"]:
            msg_id = message["id"]
            message_content, subject, sent_date = get_message_content(message)
            poem_title, author_name = parse_subject(subject)
            poem_body, poem_issue = extract_poem_details(message_content, poem_title)

            if poem_title and author_name and poem_body and poem_issue:
                poem = Poem(poem_title, author_name, poem_body, poem_issue, sent_date, msg_id)
                filename = f"{author_name}_{poem_title}.json"
                poem.save_poem_to_file(poem, filename)
                print(f"saved {filename}!")
                poems.append(poem)
                logging.debug(f"Processed and saved poem: {poem_title}")
            else:
                logging.error("Failed to process message properly")
    return poems

def main():
    logging.debug("Starting main function")
    service = setup_gmail_client()
    if service:
        query = 'from:newsletter@theparisreview.org after:1714521600 before:1716412800'
        threads = fetch_threads(service, query)
        if threads:
            poems = process_messages(service, threads)
            logging.debug(f"Processed {len(poems)} poems")
        else:
            logging.debug("No threads fetched")
    else:
        logging.error("Gmail service setup failed")

if __name__ == "__main__":
    main()
