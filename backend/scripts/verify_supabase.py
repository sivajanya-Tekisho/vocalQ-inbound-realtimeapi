import asyncio
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env vars from the backend .env file
# We assume the script is run from project root, so we point to backend/.env
# But for safety in this script, we'll confirm the path
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    sys.exit(1)

print(f"Connecting to {url} with key starting {key[:5]}...")

try:
    supabase: Client = create_client(url, key)
    
    # 1. Try to read from 'calls'
    print("Attempting to read from 'calls' table...")
    response = supabase.table("calls").select("*").limit(1).execute()
    print("Read success!")
    
    # 2. Try to insert a dummy record to check write permissions
    # We won't actually commit this if we fail, but let's try
    # If RLS is blocking, this will throw
    print("Attempting to insert dummy record...")
    # Using a fake UUID
    dummy_id = "00000000-0000-0000-0000-000000000000"
    data = {
        "call_id": dummy_id,
        "caller_number": "test_verify",
        "start_time": "2023-01-01T00:00:00Z",
        "call_status": "test"
    }
    supabase.table("calls").insert(data).execute()
    print("Insert success!")
    
    # Clean up
    supabase.table("calls").delete().eq("call_id", dummy_id).execute()
    print("Cleanup success!")
    
    print("\nVERIFICATION SUCCESSFUL: Connected, Read, and Write permissions are good.")

except Exception as e:
    print(f"\nVERIFICATION FAILED: {e}")
