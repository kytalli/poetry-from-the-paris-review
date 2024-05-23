import os
import logging
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up logging to file
log_filename = 'gmail_threads.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename,
    filemode='w'  # 'w' for write mode, 'a' for append mode
)

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
        query = 'from:paylah.alert@dbs.com after:1714521600 before:1716412800'
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

        for thread in threads:
            logging.debug(f"Processing thread ID: {thread['id']}")
            tdata = (
                service.users().threads().get(userId="me", id=thread["id"]).execute()
            )
            nmsgs = len(tdata["messages"])
            logging.debug(f"Thread ID: {thread['id']} has {nmsgs} messages")

            # Skip if <3 msgs in thread
            if nmsgs > 2:
                msg = tdata["messages"][0]["payload"]
                subject = ""
                for header in msg["headers"]:
                    if header["name"] == "Subject":
                        subject = header["value"]
                        break
                if subject:  # Skip if no Subject line
                    logging.debug(f"Thread ID: {thread['id']} Subject: {subject}")
                    print(f"- {subject}, {nmsgs}")

                # Get the message content
                message_content = "" 
                if 'parts' in msg:
                    for part in msg['parts']:
                        if part['mimeType'] == 'text/plain':
                            message_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                else:
                    message_content = base64.urlsafe_b64decode(msg['body']['data']).decode('utf-8')

                if message_content:
                    logging.debug(f"Thread ID: {thread['id']} Message Content: {message_content}")
                    print(f"Message Content: {message_content}")


        logging.debug("Completed show_chatty_threads")
        return threads

    except HttpError as error:
        logging.error(f"An error occurred: {error}")

if __name__ == "__main__":
    show_chatty_threads()
