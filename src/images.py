import requests
import logging
import os
from dotenv import load_dotenv
import random
import threading

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv()
TIMEOUT = 20
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
TOKEN_FILE = 'src/token.json'
CREDENTIALS_FILE = 'src/credentials.json'
API_KEY = os.getenv("NASA_API_KEY")

def get_google_photos_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES, redirect_uri = 'urn:ietf:wg:oauth:2.0:oob')
            # Use the out-of-band (OOB) redirect URI for console-based auth
            auth_url, _ = flow.authorization_url(prompt='consent')
            print("\nGo to the following URL in your browser and authorize access:")
            print(auth_url)
            code = input("Enter the authorization code here: ")
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

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
        except requests.exceptions.Timeout as e:
            pass
        except Exception as e:
            logging.error(f"Image retrieval error: {e}")
    raise Exception("Couldn't retrieve an image after several tries.")

class ImageProvider:
    def __init__(self, provider='nasa'):
        self.provider = provider
        self.lock = threading.Lock()
        self.next_image = None
        self.preload_event = threading.Event()
        self.thread = threading.Thread(target=self._preload_loop)
        self.thread.daemon = True
        self.thread.start()

    def _fetch(self):
        if self.provider == 'nasa':
            return get_image_nasa()
        elif self.provider == 'google_photos':
            return get_image_google_photos()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _preload_loop(self):
        while True:
            img = None
            try:
                img = self._fetch()
            except Exception as e:
                logging.error(f"Image preloading error: {e}")
            with self.lock:
                self.next_image = img
                self.preload_event.set()
            # Wait until the image is consumed before fetching another
            while True:
                with self.lock:
                    if self.next_image is None:
                        self.preload_event.clear()
                        break
                threading.Event().wait(0.2)

    def get_image(self):
        # Wait until an image is preloaded
        self.preload_event.wait()
        with self.lock:
            img = self.next_image
            self.next_image = None
        # Preloading thread will now fetch the next image
        return img

# Module-level singleton for main.py use
_provider_instance = None

def set_provider(provider='nasa'):
    global _provider_instance
    _provider_instance = ImageProvider(provider=provider)

def get_image():
    if _provider_instance is None:
        set_provider('nasa')
    return _provider_instance.get_image()
