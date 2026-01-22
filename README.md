# AutoSaaS Directory Submission Agent

An autonomous browser agent that submits SaaS products to multiple online directories using vision-based LLM reasoning and browser automation. The system is orchestrated by a FastAPI backend with PostgreSQL persistence for full observability and control.

## 🚀 Features

- **Vision-Based Automation**: Uses LLM with vision capabilities to analyze web pages and make intelligent decisions
- **Browser Automation**: Powered by Patchright with Chrome for reliable web interactions
- **Semantic Element Selection**: AgentQL for robust element targeting across different layouts
- **Job Management**: REST API for creating, monitoring, and controlling submission jobs
- **Database Persistence**: PostgreSQL for tracking jobs, attempts, and action logs
- **Concurrent Processing**: Support for multiple browser sessions running simultaneously

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL database (for production use)
- OpenAI-compatible LLM API (Groq, OpenAI, etc.)
- AgentQL API key

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AutoSaas
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install patchright browsers:**
```bash
patchright install chrome
```

### 5. Configure Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and set the following required variables:

```env
# Database (PostgreSQL)
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/autosaas

# LLM Configuration (OpenAI-compatible endpoint)
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct

# AgentQL
AGENTQL_API_KEY=your-agentql-api-key

# Browser Settings
BROWSER_HEADLESS=false
BROWSER_USER_DATA_DIR=
MAX_CONCURRENT_BROWSERS=3

# Application
MAX_RETRIES=3
SCREENSHOT_DIR=./screenshots
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here
```

**Note:** For initial testing without PostgreSQL, you can use SQLite by setting:
```env
DATABASE_URL=sqlite:///./test.db
```

### 6. Set Up Database (PostgreSQL)

If using PostgreSQL, create the database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE autosaas;
\q
```

Run Alembic migrations:

```bash
alembic upgrade head
```

## 🏃 Running the Application

### Start the FastAPI Server

**Windows:**
```powershell
python main.py
```

**macOS/Linux:**
```bash
python main.py
```

The API server will start at: `http://localhost:8000`

### Access the API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
