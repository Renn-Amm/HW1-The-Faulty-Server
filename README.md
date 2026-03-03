# Faulty API Client Lab

## Overview

This project implements a threaded client for a faulty FastAPI server.

The server:

- Exposes `/item/{item_id}`
- Is rate limited to approximately 20 requests per second
- Occasionally returns 500 errors
- Returns 429 when the rate limit is exceeded
- Provides Swagger UI at `/docs`

The server code is not modified.

The client:

- Respects the rate limit
- Handles 429 using Retry-After
- Retries 5xx errors
- Retries timeouts
- Logs retries and failures
- Writes a clean CSV file with 1000 entries

---

# Setup Instructions

## 1. Create Virtual Environment

```bash
cd faulty-api-lab
python3 -m venv venv
source venv/bin/activate
```

If using Python 3.13:

```bash
python3.13 -m venv venv
source venv/bin/activate
```

---

## 2. Install Client Dependencies

```bash
pip install httpx
```

Or if using a requirements file:

```bash
pip install -r requirements.txt
```

---

## 3. Install Provided Orders Server Package

Inside the activated virtual environment:

```bash
pip install orders_server-0.1.0.tar.gz
```

If using uv:

```bash
uv add orders_server-0.1.0.tar.gz
```

---

## 4. Start the Server

After installation:

```bash
orders_server
```

The server will start at:

```
http://127.0.0.1:8000
```

Swagger UI:

```
http://127.0.0.1:8000/docs
```

Do not modify the server code.

---

## 5. Run the Threaded Client

In another terminal with the virtual environment activated:

```bash
python client_threads.py
```

This will generate:

```
items_threads.csv
```

with approximately 1000 rows.

---

# Implementation Details

## Client Type

Threaded synchronous client  
File: `client_threads.py`

Libraries used:

- httpx
- concurrent.futures.ThreadPoolExecutor
- logging
- csv

---

# Retry Logic

Each request targets:

```
http://127.0.0.1:8000/item/{id}
```

Behavior:

### 200 OK
Data is extracted and written to CSV.

### 429 Too Many Requests
- Read `Retry-After` header
- Sleep for the specified number of seconds
- Retry the request
- Log retry at WARNING level

### 5xx Errors
- Wait 1 second
- Retry
- Log retry at WARNING level

### Other 4xx Errors
- Treated as non-retryable
- Logged at ERROR level
- Not retried

### Timeout / Transport Errors
- Retry with 1 second wait
- Limited number of attempts

---

# Rate Limiting Strategy

The client does not use hardcoded sleeps except inside retry logic.

Rate control is achieved by:

- Using a ThreadPoolExecutor with limited max_workers such as 8 to 12
- Natural request latency
- Controlled retry backoff

This keeps the request rate under the server limit and prevents overload.

The server remains responsive during execution.

---

# CSV Output

File: `items_threads.csv`

Extracted fields:

- order_id
- account_id
- company
- status
- currency
- subtotal
- tax
- total
- created_at

Nested objects such as `contact` and `lines` are excluded to keep the CSV flat and compatible with Pandas and Excel.

CSV is written using `csv.DictWriter` with proper headers and one row per order.