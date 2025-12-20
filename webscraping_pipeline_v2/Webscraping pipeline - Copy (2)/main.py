"""
STORI Annual Report Downloader
--------------------------------
This script is part of a mini-project where I built a small data pipeline that
automatically downloads annual financial report PDFs submitted to the FSMA STORI system.

The idea behind the project is:
1. Load a list of issuers from a local JSON file (saved earlier to avoid re-hitting the API).
2. For each issuer, search the STORI API for annual financial reports (starting from 2011).
3. Look through the returned items and pick only PDF documents in English or Dutch.
4. Download the PDF files using their fileDataId and save them with a formatted name.
5. Stop after a maximum number of downloads (I use 5 here for testing so I don’t overload the server).
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, List, Dict

from api_client import (
    get_http_session,
    fetch_stori_results,
    download_file,
)

# --------------------------------------------------------------------
# Logging + basic utilities
# --------------------------------------------------------------------

def setup_logging() -> None:
    """
    Creates both file and console log outputs.
    I added logging so I could easily trace what part of the process is running
    and catch issues instead of relying only on print statements.
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "stori_downloader.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logging.info("Logging initialized successfully. Log file: %s", log_file)


def sanitize_for_filename(text: str) -> str:
    """
    Clean strings so they can safely be used as filenames.
    I ran into issues with characters like spaces and parentheses,
    so this function keeps things simple and filesystem-friendly.
    """
    if not text:
        return "UNKNOWN"

    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^A-Za-z0-9_\-]+", "", text)
    return text or "UNKNOWN"


def build_output_filename(company_name: str, lei: str, publication_iso: str) -> str:
    """
    Builds filenames in the exact format requested in the assignment.

    Example result:
    ACACIA_PHARMA_GROUP_213800SLDKXWKT6E3381_AnnualReport_2022-04-29.pdf
    """
    company_part = sanitize_for_filename(company_name).upper()
    lei_part = sanitize_for_filename(lei)
    date_part = publication_iso.split("T")[0] if publication_iso else "UNKNOWN_DATE"

    return f"{company_part}_{lei_part}_AnnualReport_{date_part}.pdf"


# --------------------------------------------------------------------
# Issuer list handling (using local cached file to avoid API dependency)
# --------------------------------------------------------------------

def normalize_issuer_list(raw: Any) -> List[Dict[str, str]]:
    """
    Takes raw issuer objects from the JSON file
    and transforms them into a simplified structure.
    """
    issuers: List[Dict[str, str]] = []

    for issuer in raw:
        issuers.append({
            "id": issuer["companyId"],
            "name": issuer.get("abbreviation") or "UNKNOWN",
        })

    return issuers


def ensure_issuer_file(session, path: Path) -> List[Dict[str, str]]:
    """
    Loads issuers from a local file.
    Since the dropdown endpoint was returning errors, I switched to
    using a manually-captured copy of the issuer list.
    """
    _ = session  # I kept the parameter for later expansion

    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        issuers = normalize_issuer_list(raw)
        logging.info("Loaded %d issuers from %s", len(issuers), path)
        return issuers

    # Fallback default, only used if the file isn't present
    logging.warning(
        "Issuer file not found. Creating default entry for ACACIA PHARMA GROUP."
    )

    default_raw = [
        {
            "companyId": "02285e3c-71e9-496a-8d47-d1408131c44b",
            "companyNumber": None,
            "localisedName": None,
            "abbreviation": "ACACIA PHARMA GROUP",
            "lei": None,
        }
    ]

    path.write_text(json.dumps(default_raw, indent=2), encoding="utf-8")
    return normalize_issuer_list(default_raw)


# --------------------------------------------------------------------
# Main download logic for an individual issuer
# --------------------------------------------------------------------

def download_for_issuer(
    session,
    company_id: str,
    document_type_id: str,
    publication_start: str,
    max_downloads: int,
    already_downloaded: int,
) -> int:
    """
    Searches for report filings and then downloads PDF files.
    """
    if already_downloaded >= max_downloads:
        return already_downloaded

    # The payload structure comes directly from observing browser traffic
    search_payload = {
        "startRowIndex": 0,
        "pageSize": 50,
        "sortDirection": "Ascending",
        "documentTypeId": document_type_id,
        "isDocumentTypeGroup": False,
        "publicationStart": publication_start,
        "companyId": company_id,
    }

    logging.info("Searching STORI for companyId=%s", company_id)
    results = fetch_stori_results(session, search_payload)
    items = results.get("storiResultItems") or []

    logging.info(
        "Issuer %s: resultCount=%s, items=%s",
        company_id,
        results.get("resultCount"),
        len(items),
    )

    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)

    download_count = already_downloaded
    MAX = max_downloads

    # Loop through filings and pick documents that qualify
    for item in items:
        if download_count >= MAX:
            break

        company_name = item.get("companyName") or "UNKNOWN_COMPANY"
        lei = item.get("lei") or "NO_LEI"
        publication_iso = item.get("datePublication") or "UNKNOWN_DATE"

        documents = (item.get("mainDocuments") or []) + (item.get("attachments") or [])

        for doc in documents:
            if download_count >= MAX:
                break

            file_type = (doc.get("fileType") or "").lower()
            language = (doc.get("language") or "").lower()
            original_name = (doc.get("originalFileName") or "").lower()

            # Filter only EN/NL PDF files
            if language not in ("en", "nl"):
                continue
            if file_type != "pdf" and not original_name.endswith(".pdf"):
                continue

            file_data_id = doc.get("fileDataId")
            if not file_data_id:
                continue

            output_name = build_output_filename(company_name, lei, publication_iso)
            output_path = downloads_dir / output_name

            # If filename already exists, add version numbers
            if output_path.exists():
                stem, dot, ext = output_name.rpartition(".")
                counter = 2
                while output_path.exists():
                    output_path = downloads_dir / f"{stem}_v{counter}.{ext}"
                    counter += 1

            logging.info(
                "Downloading %s (LEI=%s) → %s",
                company_name,
                lei,
                output_path,
            )

            file_bytes = download_file(session, file_data_id)
            output_path.write_bytes(file_bytes)

            logging.info("Saved %d bytes to %s", len(file_bytes), output_path)

            download_count += 1

    return download_count


# --------------------------------------------------------------------
# Main runner
# --------------------------------------------------------------------

def main() -> None:
    """
    Coordinates the full download pipeline.
    """
    setup_logging()
    logging.info("Starting STORI Annual Report Downloader.")

    session = get_http_session()

    DOCUMENT_TYPE_ANNUAL = "9813c451-9fd4-41ba-ba7d-4e0dda0d3051"
    MAX_DOWNLOADS = 5
    total_downloads = 0

    issuers_file = Path("issuers.json.txt")
    issuers = ensure_issuer_file(session, issuers_file)

    if not issuers:
        logging.warning("No issuers found, stopping early.")
        return

    for issuer in issuers:
        if total_downloads >= MAX_DOWNLOADS:
            break

        logging.info("Processing issuer %s (%s)", issuer["name"], issuer["id"])

        total_downloads = download_for_issuer(
            session=session,
            company_id=issuer["id"],
            document_type_id=DOCUMENT_TYPE_ANNUAL,
            publication_start="2011-01-01",
            max_downloads=MAX_DOWNLOADS,
            already_downloaded=total_downloads,
        )

    logging.info("Finished. Total PDFs downloaded: %d", total_downloads)


if __name__ == "__main__":
    main()
