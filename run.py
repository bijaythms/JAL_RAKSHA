import os
import uvicorn

if __name__ == "__main__":
    print("=" * 62)
    print("  JAL-RAKSHA v4.1 - Dam Breach & Inundation Command Platform")
    print("  UI: http://127.0.0.1:8000 | API docs: /docs")
    print("=" * 62)
    uvicorn.run("app.main:app", host=os.getenv("HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "8000")), log_level="info")
