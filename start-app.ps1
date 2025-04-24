# PowerShell script to start AminoVerse application
Write-Host "Starting AminoVerse Application..." -ForegroundColor Green

# Start the backend API server in a new terminal window
Start-Process powershell -ArgumentList "-NoExit -Command `"cd '$PSScriptRoot\backend'; python run.py`""

# Wait for the backend server to start
Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Start the React frontend
Start-Process powershell -ArgumentList "-NoExit -Command `"cd '$PSScriptRoot\aminoverse'; npm start`""

Write-Host "AminoVerse services started!" -ForegroundColor Green
Write-Host "API available at: http://localhost:8000/api" -ForegroundColor Cyan
Write-Host "Frontend available at: http://localhost:3000" -ForegroundColor Cyan