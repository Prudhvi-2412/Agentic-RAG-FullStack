import requests
import json

BASE_URL = "http://localhost:8000"

def test_root():
    print("1. Testing Root API Endpoint...")
    try:
        r = requests.get(BASE_URL + "/")
        print(f"   Status Code: {r.status_code}")
        print(f"   Response Payload: {r.json()}")
    except Exception as e:
        print(f"   Connection failed: {e}")
    print("-" * 60)

def test_query_stream(query_text: str):
    print(f"2. Testing Intent-Based SSE Query: '{query_text}'")
    headers = {"Content-Type": "application/json"}
    payload = {"query": query_text}
    
    try:
        # Request stream output from the FastAPI server
        response = requests.post(
            f"{BASE_URL}/api/query", 
            json=payload, 
            headers=headers, 
            stream=True
        )
        print(f"   HTTP Status: {response.status_code}")
        print("   --- Streaming Events Start ---")
        
        # Read the Server-Sent Events line by line
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"   {decoded_line}")
                
        print("   --- Streaming Events End ---")
    except Exception as e:
        print(f"   Streaming query failed: {e}")
    print("-" * 60)

if __name__ == "__main__":
    print("============================================================")
    print("          DocuMind AI API Server Integration Test           ")
    print("============================================================\n")
    
    test_root()
    # Test General Chat (Intent Classification: GENERAL_CHAT)
    test_query_stream("Explain machine learning in one simple sentence.")
    
    # Test Document Query (Intent Classification: DOCUMENT_QUERY)
    test_query_stream("What does section 4 of the report recommend?")
