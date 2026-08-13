from contextlib import asynccontextmanager

from fastapi import FastAPI, status

from src.core.config import settings
from src.core.database import client, init_database

from src.common.utils import success_response
from src.common.exception_handler import app_exception_handler
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

app.include_router(router)

app.add_exception_handler(
    AppException,
    app_exception_handler
)


@app.get("/app ")
async def root():

    return success_response(
        data={
            "name" : settings.APP_NAME,
            "version" : settings.VERSION
        },
        message = "Welcome to Bhaktipurv"
    )