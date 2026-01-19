# AttendanceMS

A production-ready role-based facial recognition attendance management system built with FastAPI, React, and deployed on AWS ECS Fargate.

## Features

- **Facial Recognition** - Register faces and mark attendance via webcam
- **Role-Based Access Control** - Student, Lecturer, and Admin roles with granular permissions
- **Live Sessions** - Lecturers can start, pause, resume, and end attendance sessions
- **Live Camera Recognition** - Real-time face detection during active sessions with automatic attendance marking
- **Calendar View** - Visual calendar showing upcoming classes for all users
- **Student Statistics** - Detailed attendance breakdown with per-module analytics and charts
- **Real-time Dashboard** - Statistics and analytics for attendance tracking
- **Attendance Filtering** - Filter attendance records by module, session, status, and date range
- **CSV Export** - Export attendance reports for analysis
- **Modern UI** - React with Tailwind CSS and shadcn/ui components

## Tech Stack

**Backend:**
- FastAPI (Python 3.10+)
- SQLAlchemy + Alembic (PostgreSQL)
- face_recognition library
- JWT authentication

**Frontend:**
- React 18 + Vite
- TypeScript
- Tailwind CSS + shadcn/ui
- React Query + Zustand

**Infrastructure:**
- Docker multi-stage builds
- AWS ECS Fargate
- Amazon RDS PostgreSQL
- Application Load Balancer + HTTPS
- Terraform IaC

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.10+ and Node.js 18+ for local development without Docker

### Using Docker Compose

```bash
# Clone and start
git clone <repository>
cd ecsv1

# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Health:   http://localhost:8000/health
```

### Local Development (without Docker)

**Backend:**
```bash
cd app/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set environment variables
export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/attendancems
export JWT_SECRET_KEY=your-secret-key
export SEED_DEMO_DATA=true

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd app/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Demo Credentials

| Role     | Username   | Password   |
|----------|------------|------------|
| Student  | student    | student    |
| Lecturer | lecturer   | lecturer   |
| Admin    | admin      | admin      |

## API Documentation

Once running, access:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Testing

```bash
cd app/backend

# Run tests
pytest -v

# With coverage
pytest --cov=app --cov-report=html
```

## Project Structure

```
ecsv1/
├── app/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── routers/         # API endpoints
│   │   │   ├── services/        # Business logic
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   ├── auth.py          # JWT & password hashing
│   │   │   └── main.py          # FastAPI app
│   │   ├── alembic/             # Database migrations
│   │   └── tests/               # Backend tests
│   └── frontend/
│       ├── src/
│       │   ├── components/      # UI components
│       │   ├── pages/           # Page components
│       │   ├── lib/             # API client & utils
│       │   └── stores/          # Zustand stores
│       └── public/
├── infra/
│   └── terraform/               # AWS infrastructure
├── .github/
│   └── workflows/               # CI/CD pipelines
├── Dockerfile                   # Multi-stage build
├── docker-compose.yml           # Local development
└── README.md
```

## AWS Deployment

### Prerequisites
1. AWS Account with appropriate permissions
2. Route53 hosted zone for your domain
3. Terraform installed locally

### Terraform Deployment

```bash
cd infra/terraform

# Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize and apply
terraform init
terraform plan
terraform apply
```

### Manual Deployment (ClickOps)

1. **ECR:** Create repository `attendancems`
2. **RDS:** Create PostgreSQL 16 instance
3. **Secrets Manager:** Store DB credentials and JWT secret
4. **ECS:** Create Fargate cluster and service
5. **ALB:** Create Application Load Balancer with HTTPS
6. **Route53:** Create A record alias to ALB

### GitHub Actions CI/CD

Required secrets:
- `AWS_ROLE_ARN` - IAM role ARN for OIDC authentication

The pipeline will:
1. Run tests on all PRs
2. Build and push Docker image to ECR
3. Deploy to ECS Fargate on main branch pushes

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | 1440 |
| `SEED_DEMO_DATA` | Seed demo users on startup | false |
| `FACE_RECOGNITION_TOLERANCE` | Face matching tolerance | 0.6 |

## License

MIT
