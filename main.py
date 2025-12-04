import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from app.services.interview.route import router as interview_router

app = FastAPI(
    title="Writing AI API",
    description="An API for AI-powered writing assistance with topic generation and scoring.",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(interview_router, prefix="/interview", tags=["interview"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


