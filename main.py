from fastapi import FastAPI, APIRouter, status, HTTPException


APP = FastAPI(
    title="Bhaktipurv",
    version="v2.0.0"
)

@APP.get("/", status_code=status.HTTP_200_OK)
async def greeting():
    return {
        'message' : 'Welcome Bhaktipurv Backend'
    }