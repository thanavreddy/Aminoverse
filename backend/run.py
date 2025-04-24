import uvicorn
import os
import dotenv
from pathlib import Path

# Load environment variables from .env file
dotenv.load_dotenv()

if __name__ == "__main__":
    # Run the FastAPI server
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True
    )