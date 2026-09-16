from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "https://knbd8zcv-3000.inc1.devtunnels.ms",
    ],
    allow_credentials=False,   # JWT is sent via Authorization header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
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
