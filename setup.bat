@echo off
REM ============================================================
REM CrisisLink - Windows Setup Script
REM Run this from the project root: setup.bat
REM ============================================================

echo.
echo ==================================================
echo   CrisisLink - Disaster Response Coordination
echo   Setup Script for Windows
echo ==================================================
echo.

REM Check Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not running.
    echo Please install Docker Desktop from https://docker.com
    pause
    exit /b 1
)
echo [OK] Docker detected

REM Check docker-compose
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] docker-compose not found, trying docker compose...
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Docker Compose not available
        pause
        exit /b 1
    )
)
echo [OK] Docker Compose detected

REM Copy .env if not exists
if not exist .env (
    copy .env.example .env
    echo [OK] Created .env from .env.example
) else (
    echo [INFO] .env already exists, skipping
)

echo.
echo [STEP 1] Starting database services...
docker-compose up -d mysql mongodb neo4j chromadb

echo.
echo [STEP 2] Waiting for MySQL to be ready (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo [STEP 3] Starting Flask backend...
docker-compose up -d backend

echo.
echo [STEP 4] Waiting for backend to start (15 seconds)...
timeout /t 15 /nobreak >nul

echo.
echo [STEP 5] Initializing MongoDB data...
curl -s -X POST http://localhost:5000/api/mongo/init -H "Content-Type: application/json" >nul

echo.
echo [STEP 6] Starting Next.js frontend...
docker-compose up -d frontend

echo.
echo [STEP 7] Waiting for frontend to start (20 seconds)...
timeout /t 20 /nobreak >nul

echo.
echo ==================================================
echo   CrisisLink is running!
echo ==================================================
echo.
echo   Frontend:   http://localhost:3000
echo   Backend:    http://localhost:5000
echo   Neo4j:      http://localhost:7474
echo   MySQL Port: 3307
echo.
echo   Login credentials:
echo   Admin:       admin@crisislink.in / Password123!
echo   Coordinator: ravi.coordinator@ndrf.in / Password123!
echo   Citizen:     arun.kumar@gmail.com / Password123!
echo.
echo   To stop:  docker-compose down
echo   To reset: docker-compose down -v
echo ==================================================

pause
