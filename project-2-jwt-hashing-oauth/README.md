# AI Backend Project 🚀

Just another FastAPI backend with user auth. Nothing fancy, just clean code.

## What's This?

A simple user authentication API built with FastAPI and PostgreSQL. Got JWT tokens, password hashing, the usual stuff.

## Tech Stack

- **FastAPI** - Because it's fast and async
- **PostgreSQL** - Reliable database
- **SQLAlchemy** - ORM for database stuff
- **JWT** - Token-based auth
- **Bcrypt** - Password hashing (via passlib)

## Quick Start

### 1. Clone & Install

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Environment

Copy `.env.example` to `.env` and update with your actual credentials:

```bash
cp .env.example .env
```

Then edit `.env`:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/your_db
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Run It

```bash
uvicorn app.main:app --reload
```

API runs on `http://localhost:8000`

Swagger docs at `http://localhost:8000/docs` 👈 Check this out!

## API Endpoints

### Register User
```http
POST /user/register
```
**Body:**
```json
{
  "name": "John Doe",
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

### Login
```http
POST /user/login
```
**Body:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```
**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Check Auth (Protected)
```http
GET /user/is_authenticated
```
**Headers:**
```
Authorization: Bearer <your_token_here>
```
**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "username": "johndoe",
  "email": "john@example.com"
}
```

## Project Structure

```
ai_backend_project/
├── .env                    # Your secrets (don't commit this!)
├── .env.example           # Template for .env
├── .gitignore             # Keeps secrets safe
├── requirements.txt       # Python dependencies
├── README.md             # You are here
└── app/
    ├── __init__.py       # Makes it a package
    ├── main.py           # FastAPI app entry point
    ├── database.py       # DB connection & session
    ├── models.py         # User model + auth logic
    ├── schema.py         # Pydantic schemas
    └── router.py         # API routes
```

## How It Works

1. **Register** - User signs up, password gets hashed with bcrypt
2. **Login** - Verify password, return JWT token (expires in 30 min)
3. **Protected Routes** - Send token in `Authorization` header to access

## Security Features

- ✅ Passwords hashed with bcrypt
- ✅ JWT tokens for stateless auth
- ✅ Environment variables for secrets
- ✅ Token expiration (30 minutes)
- ✅ Unique username & email validation

## Notes

- Token expires in 30 minutes (configurable in `.env`)
- Make sure PostgreSQL is running before starting the app
- Database tables are auto-created on first run
- Use the Swagger docs (`/docs`) to test endpoints easily

## Common Issues

**Database connection error?**
- Check if PostgreSQL is running
- Verify `DATABASE_URL` in `.env` is correct

**Import errors?**
- Make sure you installed all dependencies: `pip install -r requirements.txt`

**Token expired?**
- Just login again to get a fresh token

---

Built with ☕ and FastAPI
