from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import boto3
from botocore.exceptions import ClientError
from lambda_handler_requests import call_login_lambda, call_chat_ask_lambda
from database.update_users import handle_user_login
from database.update_users_chats import add_user_chat
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
    try:
        handle_user_login(response) #type: ignore
    except Exception as err:
        print(f"Got error in handle_user_login: {err}")

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
    input_data = {
        "email": data.email,
        "s3_uri": None,
        "user_query": data.user_query,
        "bot_response": response["response"], #type: ignore
        "thread_id": data.thread_id,
        "query_id": data.query_id,
    }
    try:
        add_user_chat(input_data)
    except Exception as err:
        print(f"Got error in add_user_chat: {err}")

    return response


AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "hiara-dev")

try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )
    # You can add a check here to see if the bucket is accessible if you want
    # s3_client.head_bucket(Bucket=settings.s3_bucket_name)

except ClientError as e:
    # Handle potential errors, e.g., invalid credentials
    print(f"Error initializing S3 client: {e}")
    # In a real app, you might want to prevent the app from starting
    s3_client = None
except Exception as e:
    print(f"A general error occurred: {e}")
    s3_client = None


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), payload: str = Form(...)):
    """
    Uploads a file to the S3 bucket specified in the configuration.

    The file must have one of the allowed extensions:
    .pdf, .docx, .jpeg, .jpg, .png
    """
    if not s3_client:
        raise HTTPException(
            status_code=503, 
            detail="S3 client is not available. Check server configuration and credentials."
        )
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".jpeg", ".jpg", ".png"}
    # --- File Validation ---
    # Get the file extension
    filename = file.filename
    file_extension = os.path.splitext(filename)[1].lower() #type: ignore

    # Check if the file extension is in our allowed set
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Must be one of: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # --- File Upload ---
    try:
        # The key (filename in S3) will be the same as the original filename
        s3_key = "KOTAK-MAHINDRA/" + str(filename)

        # upload_fileobj streams the file directly to S3 without saving it to disk
        # This is memory-efficient. file.file is the file-like object.
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            s3_key
        )

        # Generate a presigned URL for the user to access the file (optional, but good practice)
        # This URL will be valid for 1 hour (3600 seconds)
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600
        )

    except ClientError as e:
        # Handle errors from Boto3 (e.g., bucket not found, permissions error)
        print(f"S3 Upload Error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file to S3: {e}"
        )
    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred during file upload. {e}"
        )
    finally:
        # It's good practice to close the file
        await file.close()

    data = QueryChatModel(**json.loads(payload))
    input_data = {
        "email": data.email,
        "s3_uri": file_url,
        "user_query": None,
        "bot_response": None, #type: ignore
        "thread_id": data.thread_id,
        "query_id": data.query_id,
    }
    try:
        add_user_chat(input_data)
    except Exception as err:
        print(f"Got error in add_user_chat: {err}")

    # --- Success Response ---
    return {
        "message": "File uploaded successfully",
        "filename": filename,
        "s3_bucket": S3_BUCKET_NAME,
        "s3_key": s3_key,
        "file_url": file_url # This is a temporary URL to view the file
    }
