from fastapi import FastAPI
from models import Base
from database import database_engine, sessionlocal
from router import user_router

Base.metadata.create_all(database_engine)

app = FastAPI(title="babb ki daya taa")

app.include_router(user_router)

