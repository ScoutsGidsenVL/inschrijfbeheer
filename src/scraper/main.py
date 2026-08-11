import os
from dotenv import load_dotenv

from api_requests import get_events

load_dotenv()
API_KEY = os.getenv("API_key")
ACCESS_TOKEN = os.getenv("access_token")
BASE_URL = os.getenv("base_url")

if __name__ == "__main__":
    events = get_events(BASE_URL, API_KEY, ACCESS_TOKEN)
    print(events)

