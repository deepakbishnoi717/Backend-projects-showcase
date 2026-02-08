from fastapi import APIRouter, Depends, Request, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from schema import UserSchema, UserOut, userlogin
from models import register, login as model_login, is_authenticated as model_is_authenticated

user_router = APIRouter(prefix="/user")

@user_router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(body: UserSchema, db:Session = Depends(get_db)):
    return register(body,db)

@user_router.post("/login",status_code=status.HTTP_200_OK)
def login(body:userlogin, db:Session = Depends(get_db)):
    return model_login(body, db)

@user_router.get("/is_authenticated",status_code=status.HTTP_200_OK, response_model=UserOut)
def is_authenticated(request:Request, db:Session = Depends(get_db)):
    
    return model_is_authenticated(request,db)
