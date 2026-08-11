import requests


def get_events(base: str, api_key: str, access_token: str) -> str:
    """
    Get events from the Weezevent API.

    Args:
        base (str): The base URL of the API.
        api_key (str): The API key for authentication.
        access_token (str): The access token for authentication.

    Returns:
        str: The response from the API as a string.
    """

    url = f"{base}events?api_key={api_key}&access_token={access_token}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad responses
    return response.text