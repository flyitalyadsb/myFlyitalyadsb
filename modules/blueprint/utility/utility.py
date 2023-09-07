import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

utility_bp = APIRouter()


@utility_bp.get("/favicon.ico")
def get_favicon():
    return FileResponse(os.path.join("modules", "blueprint", "utility", "templates", "favicon", "favicon.ico"),
                        media_type="image/x-icon")


@utility_bp.get("/favicon/{icon}")
def get_favicon_from_dir(icon: str):
    return FileResponse(os.path.join("modules", "blueprint", "utility", "templates", "favicon", icon),
                        media_type="image/x-icon")
