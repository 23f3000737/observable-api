import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "23f3000737@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://app-ocqnjh.example.com"

RATE_LIMIT = 10
WINDOW = 10

app = FastAPI()

# IMPORTANT:
# Add both your assigned origin and the exam page.
# During the exam, replace EXAM_ORIGIN with the actual origin
# if your instructor specifies it.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

buckets = defaultdict(deque)


@app.middleware("http")
async def middleware(request: Request, call_next):

    # Let CORS preflight pass
    if request.method == "OPTIONS":
        return await call_next(request)

    # ----------------------------
    # Request ID
    # ----------------------------
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # ----------------------------
    # Rate limiting
    # ----------------------------
    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    bucket = buckets[client]

    while bucket and bucket[0] <= now - WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            headers={
                "X-Request-ID": request_id
            },
            content={
                "detail": "Rate limit exceeded"
            }
        )

    bucket.append(now)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/ping")
def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }