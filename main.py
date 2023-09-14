from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pymongo import MongoClient
from fastapi.staticfiles import StaticFiles


app = FastAPI()


# Define Pydantic models
class UserBase(BaseModel):
    full_name: str
    email: str
    phone: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

class UserProfile(User):
    profile_picture: str

# PostgreSQL database setup
DATABASE_URL = "mysql+mysqlconnector://root@localhost/register"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    phone = Column(String)

# MongoDB setup
client = MongoClient("mongodb+srv://sangeetha18geethu:0JBeOW8roqu7In4J@cluster0.vqmvmgv.mongodb.net/?retryWrites=true&w=majority")

db = client["fastapi_db"]

@app.get("/")
def read_root():
    return {"message": "Welcome to your FastAPI application!"}

@app.post("/register", response_model=User)
def register(user: UserCreate):
    db_postgresql = SessionLocal()
    db_mongodb = db["user_profiles"]
    
    db_user = DBUser(**user.dict())
    db_postgresql.add(db_user)
    db_postgresql.commit()
    db_postgresql.refresh(db_user)
    db_postgresql.close()

    # Save profile picture to MongoDB
    profile_picture = {"user_id": db_user.id, "profile_picture": user.profile_picture}
    db_mongodb.insert_one(profile_picture)

    return User(**db_user.__dict__)

@app.get("/users/{user_id}", response_model=UserProfile)
def get_user(user_id: int):
    db_postgresql = SessionLocal()
    db_user = db_postgresql.query(DBUser).filter(DBUser.id == user_id).first()
    db_postgresql.close()

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch profile picture from MongoDB
    db_mongodb = db["user_profiles"]
    profile_picture = db_mongodb.find_one({"user_id": db_user.id})

    if profile_picture:
        user = UserProfile(**db_user.__dict__)
        user.profile_picture = profile_picture["profile_picture"]
        return user

    return UserProfile(**db_user.__dict__)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
