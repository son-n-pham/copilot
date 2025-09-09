import requests

# API endpoint URL (adjust host/port if different)
url = "http://localhost:8000/v1/process/copilot"

# Request payload
payload = {"prompt": "Analyse the files.", "files_to_upload": ["test.pdf", "test.xlsx"]}

# Send POST request
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()  # Raise error for bad status codes
    result = response.json()
    print("Success:", result)
except requests.exceptions.RequestException as e:
    print("Error:", str(e))
