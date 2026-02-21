# Start GridZen Backend (run from project root)
Write-Host "Starting GridZen Backend on http://localhost:8000 ..."
Set-Location backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
