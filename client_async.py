import asyncio
import csv
import logging

import httpx
from aiolimiter import AsyncLimiter


BASE_URL = "http://127.0.0.1:8000/item"
MAX_RETRIES = 5
OUTPUT_FILE = "items_async.csv"

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

limiter = AsyncLimiter(18, 1)
semaphore = asyncio.Semaphore(50)


async def fetch_order(client, item_id):
    url = f"{BASE_URL}/{item_id}"

    for attempt in range(MAX_RETRIES):
        try:
            async with limiter:
                async with semaphore:
                    response = await client.get(url, timeout=2.0)

            if response.status_code == 200:
                data = response.json()
                return {k: data[k] for k in FIELDS}

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logging.warning(f"429 for {item_id}")
                await asyncio.sleep(retry_after)
                continue

            if 500 <= response.status_code < 600:
                logging.warning(f"5xx for {item_id}")
                await asyncio.sleep(1)
                continue

            if 400 <= response.status_code < 500:
                logging.error(f"Non-retryable 4xx for {item_id}")
                return None

        except httpx.RequestError:
            logging.warning(f"Timeout for {item_id}")
            await asyncio.sleep(1)

    logging.error(f"Permanent failure for {item_id}")
    return None


async def main():
    results = []
    next_id = 1

    async with httpx.AsyncClient() as client:
        while len(results) < 1000:
            tasks = [
                asyncio.create_task(fetch_order(client, next_id + i))
                for i in range(50)
            ]
            next_id += 50

            responses = await asyncio.gather(*tasks)

            for res in responses:
                if res:
                    results.append(res)
                    logging.info(f"Collected {len(results)}")

                if len(results) >= 1000:
                    break

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    logging.info("CSV completed")


if __name__ == "__main__":
    asyncio.run(main())