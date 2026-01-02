import uvicorn
import traceback
import sys

if __name__ == "__main__":
    try:
        print("Starting server...")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="debug", reload=True)
    except BaseException as e:
        print(f"EXCEPTION CAUGHT ({type(e).__name__}): {e}")
        traceback.print_exc()
        sys.exit(1)
