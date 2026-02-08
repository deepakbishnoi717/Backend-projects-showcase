from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from schema import UserSchema, userlogin
from fastapi import HTTPException,Request
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from jwt import InvalidTokenError
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
exp_time = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
Base = declarative_base()

class UserModel(Base) :
    __tablename__ = "User_table"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    username = Column(String,unique=True)
    hashed_password = Column(String)
    email = Column(String,unique=True)


# Use passlib's CryptContext to avoid the missing pwdlib dependency.
password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password:str):
    return password_hash.hash(str(password))

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def register(body:UserSchema,db:Session):
    user = db.query(UserModel).filter(UserModel.username == body.username).first()
    if user:
        raise HTTPException(status_code=404, detail="username already exist!")
    
    user = db.query(UserModel).filter(UserModel.email == body.email).first()
    if user:
        raise HTTPException(status_code=404, detail="email already exist!")
    
    new_user = UserModel(
        name = body.name,
        username = body.username,
        hashed_password = get_password_hash(body.password),
        email = body.email
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"massage":"done"}


def login(body:userlogin,db:Session):
    user = db.query(UserModel).filter(UserModel.username == body.username).first()
    if not user :
        raise HTTPException(status_code=401,detail="invalid User!")
    
    if not verify_password(body.password,user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid password!")
    
    exp_time = datetime.now() + timedelta(seconds=30)
    token = jwt.encode({"id":user.id,"exp":exp_time.timestamp()},SECRET_KEY,algorithm=ALGORITHM)
    return {"token":token}


def is_authenticated(request:Request, db:Session):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing!")

    token = auth_header.split(" ")[-1]
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid token!")

    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid token!")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="invalid token!")

    return user
