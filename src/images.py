import requests
import logging
import os
from dotenv import load_dotenv
import random

load_dotenv()
TIMEOUT = 20

def get_image(provider='nasa'):
    if provider == 'nasa':
        return get_image_nasa()
    elif provider == 'google_photos':
        return get_image_google_photos()
    else:
        raise ValueError(f"Unknown provider: {provider}")

# nasa

API_KEY = os.getenv("NASA_API_KEY")

def get_image_nasa():
    if not API_KEY:
        raise Exception("NASA_API_KEY not set in environment or .env file.")
    for _ in range(5):
        try:
            resp = requests.get(
                'https://api.nasa.gov/planetary/apod',
                params={'api_key': API_KEY, 'count': 1},
                timeout=10
            )
            data = resp.json()[0]
            if data.get('media_type') == 'image':
                img_url = data['url']
                img_resp = requests.get(img_url, timeout=20)
                return img_resp.content
        except Exception as e:
            logging.error(f"Image retrieval error: {e}")
    raise Exception("Couldn't retrieve an image after several tries.")


# google photos

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

def get_google_photos_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('photoslibrary', 'v1', credentials=creds)

def get_image_google_photos():
    service = get_google_photos_service()
    results = service.mediaItems().list(pageSize=100).execute()
    items = results.get('mediaItems', [])
    if not items:
        logging.error('No media items found in Google Photos.')
        raise Exception('No media items found.')
    item = random.choice(items)
    img_resp = requests.get(item['baseUrl']+'=d', timeout=TIMEOUT)
    return img_resp.content

