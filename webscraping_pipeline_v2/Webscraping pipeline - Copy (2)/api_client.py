"""
api_client.py

This module is a small wrapper around the FSMA STORI backend API.
I separated all the HTTP logic here so that the main script can focus
on the data pipeline instead of low-level request details.
"""

import logging
from typing import Any, Dict

import requests

# Base domain for the FSMA STORI *API* (this is different from the public website).
BASE_URL: str = "https://webapi.fsma.be"

# Endpoint that returns search results as JSON.
STORI_RESULT_ENDPOINT: str = "/api/v1/en/stori/result"

# Endpoint used to download a specific document based on its fileDataId.
STORI_DOWNLOAD_ENDPOINT: str = "/api/v1/en/stori/download"


def get_http_session() -> requests.Session:
    """
    Creates a reusable HTTP session.

    I use a session instead of calling requests.get/post directly each time,
    so that the underlying TCP connection can be reused and I can set headers
    (like User-Agent) in one place.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "STORI-Downloader/1.0 (academic project)",
    })
    return session


def post_json(
    session: requests.Session,
    path: str,
    json_body: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Helper to send a POST request with a JSON body and parse the JSON response.

    This function:
    - builds the full URL using the base API URL and a relative path,
    - sends the request with a small timeout,
    - checks for HTTP errors,
    - and then tries to decode the JSON response.
    """
    url = f"{BASE_URL}{path}"
    logging.info("POST %s with JSON body: %s", url, json_body)

    try:
        response = session.post(url, json=json_body, timeout=20)
        response.raise_for_status()
    except requests.exceptions.ReadTimeout:
        logging.error("Request to %s timed out.", url)
        raise
    except requests.exceptions.RequestException as e:
        logging.error("HTTP error while calling %s: %s", url, e)
        raise

    try:
        data = response.json()
    except Exception:
        # If the server ever sends back HTML or some other format instead of JSON,
        # this log helps me see what actually came back.
        logging.error("Response from %s was not valid JSON. Raw text:", url)
        logging.error(response.text[:500])
        raise

    logging.info("Successfully received JSON response from %s", url)
    return data


def fetch_stori_results(
    session: requests.Session,
    search_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calls the STORI 'result' endpoint with the given search payload.

    The search_payload structure comes from inspecting the browser's
    network calls while using the STORI web interface.

    The response usually contains:
      - resultCount
      - storiResultItems (list of filings)
    """
    return post_json(session, STORI_RESULT_ENDPOINT, search_payload)


def download_file(
    session: requests.Session,
    file_data_id: str,
) -> bytes:
    """
    Downloads a single file from STORI using its fileDataId.

    In the browser this is equivalent to:
        GET https://webapi.fsma.be/api/v1/en/stori/download?fileDataId=...

    Here I return the raw bytes so the caller can decide how to save the file.
    """
    url = f"{BASE_URL}{STORI_DOWNLOAD_ENDPOINT}"
    params = {"fileDataId": file_data_id}

    logging.info("Downloading fileDataId=%s from %s", file_data_id, url)

    try:
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("Error downloading fileDataId=%s: %s", file_data_id, e)
        raise

    logging.info(
        "Downloaded %d bytes for fileDataId=%s (Content-Type: %s)",
        len(response.content),
        file_data_id,
        response.headers.get("Content-Type"),
    )

    return response.content
