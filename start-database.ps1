# PowerShell script to start PostgreSQL and Redis using Docker Compose
# Run this in PowerShell: .\start-database.ps1

Write-Host "Starting PostgreSQL 16 with PostGIS and Redis..." -ForegroundColor Green

# Start Docker Compose services
docker compose up -d

# Wait for services to be ready
Write-Host "Waiting for database to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if PostgreSQL is running
$pgStatus = docker compose ps postgres 2>&1
$redisStatus = docker compose ps redis 2>&1

if ($pgStatus -match "Up") {
    Write-Host "✓ PostgreSQL is running on port 5432" -ForegroundColor Green
} else {
    Write-Host "✗ PostgreSQL failed to start" -ForegroundColor Red
}

if ($redisStatus -match "Up") {
    Write-Host "✓ Redis is running on port 6379" -ForegroundColor Green
} else {
    Write-Host "✗ Redis failed to start" -ForegroundColor Red
}

Write-Host "`nYou can now run Alembic migrations:" -ForegroundColor Cyan
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  ..\venv\Scripts\alembic.exe revision --autogenerate -m 'Initial schema'" -ForegroundColor White
Write-Host "  ..\venv\Scripts\alembic.exe upgrade head" -ForegroundColor White
