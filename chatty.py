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

# Set up logging to file
log_filename = 'gmail_threads.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename,
    filemode='w'  # 'w' for write mode, 'a' for append mode
)

@attr.s
class Poem:
    title = attr.ib()
    author = attr.ib()
    body = attr.ib()
    issue = attr.ib()
    sent_date = attr.ib()
    msg_id = attr.ib()

    def to_json(self):
        """Converts the Poem object into a JSON string."""
        return json.dumps(attr.asdict(self), indent=4)

    @classmethod
    def from_json(cls, json_str):
        """Creates a Poem object from a JSON string."""
        data = json.loads(json_str)
        return cls(**data)
    
    def save_poem_to_file(poem, filename):
        """Saves the poem JSON to a file."""
        with open(filename, 'w') as f:
            f.write(poem.to_json())

    def load_poem_from_file(filename):
        """Loads a poem JSON from a file and returns a Poem object."""
        with open(filename, 'r') as f:
            json_str = f.read()
        return Poem.from_json(json_str)


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
    print("debug: examining subject ->", repr(subject))
    
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
            print(poem_title)
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


# Define the required scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def show_chatty_threads():
    """Display threads with long conversations (>= 3 messages)
    Return: None

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = None
    logging.debug("Starting show_chatty_threads")

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        logging.debug("token.json found")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        logging.error("token.json not found")
        return

    try:
        # Create Gmail API client
        logging.debug("Building Gmail API client")
        service = build("gmail", "v1", credentials=creds)
        threads = []
        page_token = None
        query = 'from:newsletter@theparisreview.org after:1714521600 before:1716412800'
        logging.debug(f"Query: {query}")

        while True:
            logging.debug(f"Fetching threads with pageToken: {page_token}")
            response = service.users().threads().list(
                userId="me", 
                pageToken=page_token, 
                q=query
            ).execute()
            fetched_threads = response.get("threads", [])
            logging.debug(f"Fetched {len(fetched_threads)} threads")
            threads.extend(fetched_threads)
            page_token = response.get("nextPageToken")
            if not page_token:
                logging.debug("No more pages to fetch")
                break

        poems = []  # List to store Poem objects
        for thread in threads:
            logging.debug(f"Processing thread ID: {thread['id']}")
            tdata = (
                service.users().threads().get(userId="me", id=thread["id"]).execute()
            )
            nmsgs = len(tdata["messages"])
            logging.debug(f"Thread ID: {thread['id']} has {nmsgs} messages")

            for message in tdata["messages"]:
                msg_id = message["id"]
                message_detail = service.users().messages().get(userId="me", id=msg_id).execute()
                message_content, subject, sent_date = get_message_content(message)
                poem_title, author_name = parse_subject(subject)
                if poem_title and author_name:
                    print("Poem Title:", poem_title)
                    print("Author Name:", author_name)
                else:
                    print("Failed to parse subject")    
                poem_body, poem_issue = extract_poem_details(message_content, poem_title)
                if poem_body and poem_issue:
                    print("poem body:", poem_body)
                    print("poem issue:", poem_issue)
                    # Create a Poem object and add it to the list
                    poem = Poem(poem_title, author_name, poem_body, poem_issue, sent_date, msg_id)
                    poems.append(poem)
                    filename = f"{author_name}_{poem_title}"
                    poem.save_poem_to_file

                else:
                    print("Failed to extract poem details")
            else:
                print("Failed to parse subject")


        logging.debug("Completed show_chatty_threads")
        return threads
    
    except HttpError as error:
        logging.error(f"An error occurred: {error}")



if __name__ == "__main__":
    show_chatty_threads()
