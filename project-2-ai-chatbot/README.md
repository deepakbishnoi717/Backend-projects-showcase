# Backend Projects Portfolio 🚀

A collection of backend projects showcasing modern web development practices, API design, and authentication systems.

Built with **FastAPI**, **PostgreSQL**, and clean architecture principles.

---

## 📂 Projects Overview

### Project 1: ATM Banking System (Full-Stack)
[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen?style=for-the-badge&logo=render)](https://atm-banking-system.onrender.com)

A premium full-stack banking application with transaction management and real-time UI.

**Tech Stack:** FastAPI, PostgreSQL, Vanilla JavaScript, Glassmorphism UI

**Key Features:**
- 💰 Transaction management with atomic commits
- 🎨 Premium glassmorphism UI design
- 📊 Real-time balance updates
- 🔒 Account validation and security

[View Project Details →](./Project-1/README.md)

---

### Project 2: JWT, Hashing & OAuth Authentication

A production-ready authentication API implementing industry-standard security practices.

**Tech Stack:** FastAPI, PostgreSQL, JWT, Bcrypt, SQLAlchemy

**Key Features:**
- 🔐 JWT token-based authentication
- 🔒 Bcrypt password hashing
- 👤 User registration & login
- ⏱️ Token expiration management
- 🛡️ Protected route middleware
- 📝 Environment-based configuration

[View Project Details →](./project-2-jwt-hashing-oauth/README.md)

---

## 🛠️ Tech Stack Across Projects

| Technology | Purpose |
|:-----------|:--------|
| **FastAPI** | High-performance async web framework |
| **PostgreSQL** | Robust relational database |
| **SQLAlchemy** | Python ORM for database operations |
| **JWT** | Stateless authentication tokens |
| **Bcrypt** | Secure password hashing |
| **Pydantic** | Data validation and serialization |
| **Uvicorn** | ASGI server for production |

---

## 🚀 Quick Start

Each project has its own setup instructions. General workflow:

### 1. Clone the Repository
```bash
git clone https://github.com/deepakbishnoi717/Month-1-All-Project.git
cd Month-1-All-Project
```

### 2. Navigate to a Project
```bash
cd project-2-jwt-hashing-oauth  # or Project-1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 5. Run the Application
```bash
uvicorn app.main:app --reload
```

---

## 📚 What I Learned

### Backend Development
- RESTful API design patterns
- Database modeling with SQLAlchemy
- Authentication & authorization flows
- Environment-based configuration
- Error handling and validation

### Security Best Practices
- Password hashing with bcrypt
- JWT token generation and validation
- Protecting sensitive routes
- Environment variable management
- SQL injection prevention via ORM

### DevOps & Deployment
- Git version control
- Environment separation (dev/prod)
- Database migrations
- API documentation with Swagger

---

## 🎯 Project Structure

```
Month-1-All-Project/
├── Project-1/                          # ATM Banking System
│   ├── backend/                        # FastAPI backend
│   ├── frontend/                       # Vanilla JS frontend
│   └── README.md
│
├── project-2-jwt-hashing-oauth/       # Authentication API
│   ├── app/
│   │   ├── main.py                    # FastAPI app
│   │   ├── models.py                  # User model & auth logic
│   │   ├── database.py                # DB connection
│   │   ├── router.py                  # API routes
│   │   └── schema.py                  # Pydantic schemas
│   ├── .env.example                   # Environment template
│   ├── requirements.txt               # Dependencies
│   └── README.md
│
└── README.md                          # This file
```

---

## 🔥 Key Highlights

### Clean Code Practices
- ✅ Separation of concerns (models, routes, schemas)
- ✅ Type hints and Pydantic validation
- ✅ Environment-based configuration
- ✅ Comprehensive error handling

### Security First
- ✅ No hardcoded credentials
- ✅ Password hashing (bcrypt)
- ✅ JWT token authentication
- ✅ Protected routes with middleware
- ✅ `.gitignore` for sensitive files

### Production Ready
- ✅ PostgreSQL for data persistence
- ✅ SQLAlchemy ORM
- ✅ Async FastAPI endpoints
- ✅ Auto-generated API docs (Swagger)
- ✅ Proper dependency management

---

## 📈 Future Enhancements

- [ ] OAuth2 integration (Google, GitHub)
- [ ] Rate limiting and throttling
- [ ] Redis for session management
- [ ] Email verification system
- [ ] Role-based access control (RBAC)
- [ ] API versioning
- [ ] Comprehensive test coverage
- [ ] Docker containerization

---

## 🤝 Connect

Built by **Deepak Bishnoi** | Backend Developer

Learning, building, and shipping production-ready backends 🚀

---

**Note:** Each project contains its own detailed README with setup instructions, API documentation, and technical details.
