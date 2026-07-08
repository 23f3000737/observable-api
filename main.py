import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Header, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

TOTAL_ORDERS = 58
RATE_LIMIT = 18
WINDOW = 10  # seconds

# ----------------------------
# Fixed catalog
# ----------------------------
catalog = [
    {
        "id": i,
        "item": f"Item {i}",
        "price": float(i * 10),
    }
    for i in range(1, TOTAL_ORDERS + 1)
]

# ----------------------------
# Stores
# ----------------------------
idempotency_store = {}
client_requests = defaultdict(deque)


# ----------------------------
# Rate Limiting Middleware
# ----------------------------
@app.middleware("http")
async def rate_limit(request: Request, call_next):

    # Allow CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()
    bucket = client_requests[client_id]

    # Remove expired timestamps
    while bucket and bucket[0] <= now - WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        retry_after = max(1, int(WINDOW - (now - bucket[0])))

        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={"detail": "Rate limit exceeded"},
        )

    bucket.append(now)

    response = await call_next(request)
    return response


# ----------------------------
# POST /orders
# ----------------------------
@app.post("/orders", status_code=201)
def create_order(
    body: dict = Body(default={}),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "status": "created",
        "order": body,
    }

    idempotency_store[idempotency_key] = order

    return order


# ----------------------------
# GET /orders
# ----------------------------
@app.get("/orders")
def list_orders(
    limit: int = Query(10, ge=1),
    cursor: str | None = None,
):
    start = int(cursor) if cursor else 0

    items = catalog[start:start + limit]

    next_cursor = (
        str(start + limit)
        if start + limit < TOTAL_ORDERS
        else None
    )

    return {
        "items": items,
        "next_cursor": next_cursor,
    }