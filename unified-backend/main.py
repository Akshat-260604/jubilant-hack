from fastapi import FastAPI
from api.v1.routes import router
from configs.config import AppInfo
from fastapi.middleware.cors import CORSMiddleware


def create_application() -> FastAPI:
    info = AppInfo()
    
    application = FastAPI(
        title=info.PROJECT_NAME,
        version=info.VERSION,
        description=info.DESCRIPTION,
        openapi_url=f"{info.API_V1_STR}/vectoriser/openapi.json"
    )
    
    application.add_middleware(
        CORSMiddleware,
        allow_origins=info.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    application.include_router(router, prefix=info.API_V1_STR)
    return application

app = create_application()