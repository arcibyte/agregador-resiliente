# se puede arrancar el servidor tanto con `uvicorn main:app` como con `uvicorn app.main:app`.

import uvicorn
from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
