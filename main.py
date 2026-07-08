import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Allow browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 58
RATE_LIMIT = 18
WINDOW = 10  # seconds

# -----------------------------
# Fixed catalog (IDs 1..58)
# -----------------------------
catalog = [
    {
        "id": i,
        "item": f"Item {i}",
        "price": float(i * 10)
    }
    for i in range(1, TOTAL_ORDERS + 1)
]

# -----------------------------
# Idempotency storage
# -----------------------------
idempotency_store = {}

# -----------------------------
# Rate limiting
# -----------------------------
client_requests = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request, call_next):

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    bucket = client_requests[client_id]

    while bucket and bucket[0] <= now - WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        retry_after = max(1, int(WINDOW - (now - bucket[0])))

        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(retry_after)
            },
            content={
                "detail": "Rate limit exceeded"
            },
        )

    bucket.append(now)

    return await call_next(request)


# ---------------------------------------------------
# POST /orders
# ---------------------------------------------------

@app.post("/orders", status_code=201)
def create_order(
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "status": "created"
    }

    idempotency_store[idempotency_key] = order

    return order


# ---------------------------------------------------
# GET /orders
# ---------------------------------------------------

@app.get("/orders")
def list_orders(
    limit: int = Query(10, ge=1),
    cursor: str | None = None
):

    start = 0

    if cursor:
        start = int(cursor)

    items = catalog[start:start + limit]

    next_cursor = None

    if start + limit < TOTAL_ORDERS:
        next_cursor = str(start + limit)

    return {
        "items": items,
        "next_cursor": next_cursor
    }