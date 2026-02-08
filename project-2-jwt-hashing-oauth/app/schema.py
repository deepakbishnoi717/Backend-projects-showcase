from pydantic import BaseModel, ConfigDict

class UserSchema(BaseModel) :
    name : str 
    username : str
    email : str
    password : str


class UserOut(BaseModel):
    id: int
    name: str
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)
    

class userlogin(BaseModel):
    username:str
    password : str
    
