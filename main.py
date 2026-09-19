import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.core.config import settings
from src.core.database import client, init_database

from src.common.utils import success_response
from src.common.exception_handler import app_exception_handler, generic_exception_handler
from src.common.exceptions import AppException

from src.api.router import router


@asynccontextmanager
async def lifespan(app : FastAPI):

    # start
    print("Application starting...")


    try:
        await client.admin.command("ping")
        await init_database()
        print("MongoDB connected..")

    except Exception as e:
        print("Database connection failed")
        raise e


    yield

    # shutdown
    print("Closing application")

    client.close()



app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    description="",
    version= settings.VERSION
)

# 1. Timing Middleware: Measures internal FastAPI / Database processing time
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"
    return response

# 2. GZip Compression: Compresses responses larger than 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. CORS Middleware: Caches preflight OPTIONS requests for 24 hours (86400s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

app.include_router(router)

app.add_exception_handler(
    AppException,
    app_exception_handler
)

app.add_exception_handler(
    Exception,
    generic_exception_handler
)


@app.get("/app")
async def root():

    return success_response(
        data={
            "name" : settings.APP_NAME,
            "version" : settings.VERSION
        },
        message = "Welcome to BhaktiParv"
    )
