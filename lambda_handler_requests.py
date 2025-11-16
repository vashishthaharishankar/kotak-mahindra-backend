import requests
import json

# --- CONFIGURATION ---
# IMPORTANT: Replace this with the "Invoke URL" from your AWS API Gateway deployment
API_BASE_URL = "https://rc65jvqe43f5gwshmio73q56vq0gbhge.lambda-url.ap-south-1.on.aws"

# ---------------------

def call_login_lambda(first_name: str, last_name: str, email: str, provider: str):
    """
    Calls the /login endpoint on your Lambda function.
    """
    url = f"{API_BASE_URL}/login"
    
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "provider": provider
    }
    
    print(f"Sending POST request to {url} with payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(url, json=payload)
        
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status() 
        
        print(f"\nSuccess! Status Code: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
        
    except requests.exceptions.HTTPError as http_err:
        print(f"\nHTTP error occurred: {http_err}")
        print(f"Response Body: {response.text}")
    except requests.exceptions.RequestException as err:
        print(f"\nAn error occurred: {err}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        
    return None

def call_chat_ask_lambda(first_name: str, email: str, user_query: str, thread_id: str, 
                  last_name: str  = "", provider: str = "google", query_id: str = "q_123"):
    """
    Calls the /api/chat/ask endpoint on your Lambda function.
    """
    url = f"{API_BASE_URL}/api/chat/ask"
    
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "provider": provider,
        "user_query": user_query,
        "thread_id": thread_id,
        "query_id": query_id
    }
    
    print(f"Sending POST request to {url} with payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        print(f"\nSuccess! Status Code: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
        
    except requests.exceptions.HTTPError as http_err:
        print(f"\nHTTP error occurred: {http_err}")
        print(f"Response Body: {response.text}")
    except requests.exceptions.RequestException as err:
        print(f"\nAn error occurred: {err}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        
    return None

if __name__ == "__main__":
    # --- Example 1: Test the /login endpoint ---
    print("\n" + "="*20 + " TESTING /login " + "="*20)
    call_login_lambda(
        first_name="ApiClient",
        last_name="TestUser",
        email="api.client@example.com",
        provider="google"
    )
    
    # --- Example 2: Test the /api/chat/ask endpoint ---
    print("\n" + "="*20 + " TESTING /api/chat/ask " + "="*20)
    call_chat_ask_lambda(
        first_name="ApiClient",
        email="api.client@example.com",
        user_query="What is the capital of France?",
        thread_id="thread_client_123"
    )
