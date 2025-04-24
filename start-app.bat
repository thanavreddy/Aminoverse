@echo off
echo Starting AminoVerse Application...

:: Start the backend API server in a new terminal window
start cmd /k "cd backend && python run.py"

:: Wait for the backend server to start
echo Waiting for backend to start...
timeout /t 5

:: Start the React frontend
start cmd /k "cd aminoverse && npm start"

echo AminoVerse services started!
echo API available at: http://localhost:8000/api
echo Frontend available at: http://localhost:3000