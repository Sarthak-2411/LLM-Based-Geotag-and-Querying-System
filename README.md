# LLM-Based-Geotag-and-Querying-System

This project is a Streamlit application for extracting geographic locations from disaster-related text using a Large Language Model (LLM) and visualizing the extracted locations on an interactive map.

## Project Structure

```
.
├── .raw_articles/
├── .streamlit/
│   └── secrets.toml
├── indexes/
├── final_streamlit_app.py
├── requirements.txt
├── states_india.geojson
└── README.md
```

---

## Prerequisites

- Python **3.12.10**
- pip

---

## 1. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 2. Install Dependencies

Install all required packages using:

```bash
pip install -r requirements.txt
```

---

## 3. Configure Google API Key

Create a file named:

```
.streamlit/secrets.toml
```

Add your Google API key from https://aistudio.google.com/api-keys in the following format:

```toml
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
```

Replace `YOUR_GOOGLE_API_KEY` with your actual API key.

---

## 4. Run the Application

Start the Streamlit application using:

```bash
streamlit run final_streamlit_app.py
```

The application will open automatically in your default web browser.

---

## Notes

- Ensure `states_india.geojson` is present in the project root directory.
- The `.streamlit/secrets.toml` file should **not** be committed to version control.
- The `indexes/` directory stores the vector indexes required by the application.
- The `.raw_articles/` directory contains the raw scraped articles used by the application.

---

## Python Version

This project has been tested with:

```
Python 3.12.10
```