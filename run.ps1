# Check if virtual environment exists
if (Test-Path -Path ".\venv") {
    Write-Host "Activating virtual environment and starting Streamlit..." -ForegroundColor Cyan
    & ".\venv\Scripts\streamlit" run src/main.py
} else {
    Write-Error "Virtual environment 'venv' not found. Please run installation setup."
}
