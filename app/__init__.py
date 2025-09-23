from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.response_utils import error_response

load_dotenv()

def create_app():
    app = FastAPI()

    # --- MOUNT STATIC FILES ---
    # serve CSS/JS under /static, and index.html at root
    

    # --- API ROUTES ---
    from .main import router
    app.include_router(router)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/",       StaticFiles(directory="app/static", html=True), name="frontend")

    # --- GLOBAL EXCEPTION HANDLERS ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        messages = []
        for e in exc.errors():
            loc = " -> ".join(map(str, e["loc"]))
            msg = e["msg"]
            messages.append(f"{loc}: {msg}")
        return error_response("Validation error: " + " | ".join(messages), status_code=422)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return error_response(f"Unhandled server error: {str(exc)}", status_code=500)

    return app
