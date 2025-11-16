from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from lambda_handler_requests import call_login_lambda, call_chat_ask_lambda
# from rag_pipeline import main_execution_flow
# from salesforce_client import create_salesforce_lead


load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserLoginData(BaseModel):
    first_name: str
    last_name: str | None = None  # Optional
    email: str
    provider: str  # "google" or "microsoft"


class QueryChatModel(BaseModel):
    first_name: str
    last_name: str | None = None
    email: str
    provider: str
    user_query: str
    thread_id: str
    query_id: str


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")


# --- API Endpoint ---
@app.post("/login")
async def create_lead_in_salesforce(user: UserLoginData):
    response = call_login_lambda(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        provider=user.provider,
    )

    return response


# --- API Endpoint ---
@app.post("/api/chat/ask")
async def ask(data: QueryChatModel):
    response = call_chat_ask_lambda(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        provider=data.provider,
        user_query=data.user_query,
        thread_id=data.thread_id,
        query_id=data.query_id,
    )

    return response
