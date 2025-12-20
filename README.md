 

* what the project does
* why it exists
* how it works
* how to run it
* how it can be extended (especially to healthcare APIs)

This is **research-grade documentation**, not a student README.

---

# 📄 STORI Data Ingestion Pipeline

**Automated Collection of Regulatory Filings via Public APIs**

---

## 📌 Project Overview

This project implements a **reproducible data ingestion pipeline** that programmatically collects annual financial report documents from the **Belgian Financial Services and Markets Authority (FSMA) STORI system**.

Instead of manually navigating the STORI web interface, the pipeline **communicates directly with the underlying backend API**, retrieves structured metadata in JSON format, filters relevant documents, and downloads the associated PDF files using a **consistent, machine-readable naming convention**.

The project is designed to demonstrate **core data engineering concepts**, including:

* API-based data collection
* Processing semi-structured data (JSON)
* Modular pipeline architecture
* Robust logging and error handling
* Reproducibility and extensibility for research use

Although the current implementation targets **financial regulatory filings**, the architecture is **domain-agnostic** and can be reused for other public data sources such as **healthcare, clinical research, or government open-data APIs**.

---

## 🎯 Key Objectives

The pipeline was built to:

1. Programmatically collect data from a public backend API
2. Avoid browser automation or manual downloads
3. Transform semi-structured API responses into a clean, organized local dataset
4. Ensure reproducibility through logging and documentation
5. Provide a clear foundation for future extensions (e.g., CSV extraction, NLP, databases)

---

## 🏗️ System Architecture

The project follows a **clean separation of concerns**:

```
Offline issuer list (JSON)
        ↓
     main.py
        ↓
   api_client.py
        ↓
   STORI Backend API (JSON)
        ↓
   Filter & Validation Logic
        ↓
   PDF Downloads (Structured Filenames)
```

### Architectural Principles

* **Modularity**: All HTTP logic is isolated from business logic
* **Reproducibility**: Logging replaces print statements
* **Safety**: Download limits prevent server overload
* **Extensibility**: Clear boundaries for adding new outputs (CSV, DB, NLP)

---

## 📁 Project Structure

```
stori-data-ingestion-pipeline/
├── src/
│   ├── main.py              # Pipeline orchestration logic
│   └── api_client.py        # Low-level API communication
├── data/
│   └── issuers.json.txt     # Cached list of issuers (offline)
├── downloads/               # Downloaded PDF files (created at runtime)
├── logs/
│   └── stori_downloader.log # Execution logs
├── docs/
│   └── Webscraping_Report.pdf
├── requirements.txt
└── README.md
```

> **Note:** The `downloads/` and `logs/` folders are created automatically when the pipeline runs.

---

## 🔌 Data Source: FSMA STORI System

The **STORI platform** is the official Belgian repository for regulated information filings.

### Backend API Endpoints Used

The STORI web interface communicates with a JSON-based backend API. This project uses two endpoints:

1. **Search endpoint**

```
POST https://webapi.fsma.be/api/v1/en/stori/result
```

Returns structured metadata including:

* Issuer name
* LEI
* Publication date
* Document metadata
* File identifiers (`fileDataId`)

2. **Download endpoint**

```
GET https://webapi.fsma.be/api/v1/en/stori/download?fileDataId=...
```

Returns raw binary data (PDF files).

---

## 🧠 Design Decisions

### Why API-based ingestion?

* Faster and more reliable than browser automation
* Avoids fragile UI scraping
* Produces structured, machine-readable data

### Why separate `api_client.py`?

* Centralizes all network logic
* Simplifies debugging and testing
* Makes the pipeline reusable for other APIs

### Why local issuer cache?

* Avoids repeated API calls
* Improves reproducibility
* Allows offline testing

---

## ⚙️ How the Pipeline Works

When executed, the pipeline performs the following steps:

1. **Initialize logging**

   * Logs are written to both console and file

2. **Create HTTP session**

   * Custom User-Agent
   * Connection reuse via `requests.Session`

3. **Load issuer list**

   * Reads from `issuers.json.txt`
   * Normalizes issuer identifiers

4. **Search for filings**

   * Queries the STORI API for each issuer
   * Filters by document type: *Annual financial report*
   * Restricts results to publications from 2011 onward

5. **Filter documents**

   * Language: English or Dutch only
   * File type: PDF only

6. **Download files**

   * Downloads using `fileDataId`
   * Saves files with deterministic names
   * Prevents overwriting via versioned filenames

7. **Enforce global limits**

   * Stops after a configurable maximum number of downloads

---

## 🧾 File Naming Convention

Downloaded files follow this strict pattern:

```
ISSUERNAME_LEI_AnnualReport_YYYY-MM-DD.pdf
```

Example:

```
ACACIA_PHARMA_GROUP_213800SLDKXWKT6E3381_AnnualReport_2022-04-29.pdf
```

This ensures:

* Easy sorting
* Programmatic parsing
* Compatibility with downstream pipelines

---

## 🛠️ Requirements

* Python **3.8+** (tested with Python 3.10)
* Internet access
* Python dependency:

```
requests
```

---

## 🚀 Setup Instructions

### 1. Clone or copy the project

```bash
git clone <repository-url>
cd stori-data-ingestion-pipeline
```

### 2. (Optional) Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Ensure issuer file exists

Verify that:

```
data/issuers.json.txt
```

is present and contains issuer objects with `companyId` fields.

---

## ▶️ Running the Pipeline

Execute:

```bash
python src/main.py
```

During execution you will see:

* API requests being made
* Files being downloaded
* Logs written to `logs/stori_downloader.log`

---

## ⚠️ Configuration Options

Inside `main.py`:

* **Maximum number of downloads**

```python
MAX_DOWNLOADS = 5
```

* **Document type ID**

```python
DOCUMENT_TYPE_ANNUAL = "9813c451-9fd4-41ba-ba7d-4e0dda0d3051"
```

* **Issuer file path**

```python
issuers_file = Path("data/issuers.json.txt")
```

---

## 🧪 Error Handling & Logging

The pipeline includes:

* HTTP timeout handling
* Request exception logging
* JSON decoding safeguards
* File collision protection

All issues are logged to:

```
logs/stori_downloader.log
```

---

## 🔄 Extensibility & Future Work

This pipeline is intentionally designed to be extended. Possible next steps include:

* Extracting metadata into CSV files
* Storing results in a relational database (PostgreSQL / SQLite)
* Running NLP on downloaded PDFs
* Parallelizing downloads
* Adapting the API client for healthcare data sources such as:

  * ClinicalTrials.gov
  * NIH Open Data APIs
  * CDC public datasets

---

## 📚 Academic & Research Context

This project demonstrates applied skills in:

* Data engineering
* API reverse-engineering
* Reproducible research pipelines
* Programmatic data collection

It is suitable for:

* Research assistantships
* Data engineering internships
* Graduate-level project portfolios

---

## 👤 Author

**Gold Nwobu**
M.S. Computer Science
November 2025

---

 
