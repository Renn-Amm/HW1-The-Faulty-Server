import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


import httpx

BASE_URL = "http://127.0.0.1:8000/item"
MAX_WORKERS = 10
MAX_RETRIES = 5
OUTPUT_FILE = "items_threads.csv"

FIELDS = [
    "order_id",
    "account_id",
    "company",
    "status",
    "currency",
    "subtotal",
    "tax",
    "total",
    "created_at",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def fetch_order(client, item_id):
    url = f"{BASE_URL}/{item_id}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.get(url, timeout=2.0)

            if response.status_code == 200:
                data = response.json()
                return {k: data[k] for k in FIELDS}

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logging.warning(f"429 for {item_id}, sleeping {retry_after}s")
                time.sleep(retry_after)
                continue

            if 500 <= response.status_code < 600:
                logging.warning(f"5xx for {item_id}, retrying in 1s")
                time.sleep(1)
                continue

            if 400 <= response.status_code < 500:
                logging.error(f"Non-retryable 4xx for {item_id}")
                return None

        except httpx.RequestError:
            logging.warning(f"Timeout/transport error for {item_id}")
            time.sleep(1)

    logging.error(f"Permanent failure for {item_id}")
    return None


def main():
    results = []
    next_id = 1

    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}

            while len(results) < 1000:
                while len(futures) < MAX_WORKERS:
                    futures[executor.submit(fetch_order, client, next_id)] = next_id
                    next_id += 1

                for future in as_completed(futures):
                    futures.pop(future)
                    result = future.result()
                    if result:
                        results.append(result)
                        logging.info(f"Collected {len(results)}")

                    if len(results) >= 1000:
                        break

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    logging.info("CSV completed")


if __name__ == "__main__":
    main()