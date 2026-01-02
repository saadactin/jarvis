# Helper script to update DATABASE_URL in .env file

Write-Host "`n=== Database Setup Helper ===" -ForegroundColor Cyan
Write-Host "`nThis script will help you update the DATABASE_URL in your .env file`n" -ForegroundColor Yellow

# Get PostgreSQL username
$username = Read-Host "Enter PostgreSQL username (default: postgres)"
if ([string]::IsNullOrWhiteSpace($username)) {
    $username = "postgres"
}

# Get PostgreSQL password
$password = Read-Host "Enter PostgreSQL password" -AsSecureString
$passwordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

# Get database name
$dbName = Read-Host "Enter database name (default: jarvis_db)"
if ([string]::IsNullOrWhiteSpace($dbName)) {
    $dbName = "jarvis_db"
}

# Get host (optional)
$host = Read-Host "Enter PostgreSQL host (default: localhost)"
if ([string]::IsNullOrWhiteSpace($host)) {
    $host = "localhost"
}

# Get port (optional)
$port = Read-Host "Enter PostgreSQL port (default: 5432)"
if ([string]::IsNullOrWhiteSpace($port)) {
    $port = "5432"
}

# Construct DATABASE_URL
$dbUrl = "postgresql://${username}:${passwordPlain}@${host}:${port}/${dbName}"

Write-Host "`nUpdating .env file..." -ForegroundColor Green

# Update .env file
$envContent = Get-Content .env -Raw
$envContent = $envContent -replace "DATABASE_URL=.*", "DATABASE_URL=$dbUrl"
$envContent | Set-Content .env -Encoding utf8

Write-Host "✓ DATABASE_URL updated successfully!" -ForegroundColor Green
Write-Host "`nUpdated DATABASE_URL:" -ForegroundColor Cyan
Write-Host "  $dbUrl" -ForegroundColor Gray

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Make sure PostgreSQL is running" -ForegroundColor White
Write-Host "2. Create the database if it doesn't exist:" -ForegroundColor White
Write-Host "   createdb -U $username $dbName" -ForegroundColor Gray
Write-Host "   OR" -ForegroundColor Gray
Write-Host "   psql -U $username -c 'CREATE DATABASE $dbName;'" -ForegroundColor Gray
Write-Host "3. Run: python jarvis-main/init_db.py" -ForegroundColor White
Write-Host "4. Start the backend: python jarvis-main/app.py`n" -ForegroundColor White

