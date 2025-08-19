# Deploy Backend to Railway
Write-Host "🚀 Deploying My Own LLM Backend to Railway..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "backend\railway.json")) {
    Write-Host "❌ Error: railway.json not found. Make sure you're in the project root." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Railway config found!" -ForegroundColor Green

# Open Railway deployment page
Write-Host "🌐 Opening Railway deployment page..." -ForegroundColor Yellow
Start-Process "https://railway.app/new"

Write-Host ""
Write-Host "📋 Manual Deployment Steps:" -ForegroundColor Cyan
Write-Host "1. Click 'Deploy from GitHub repo'" -ForegroundColor White
Write-Host "2. Select your repo: Ali-jpg-cmd/My-own-llm" -ForegroundColor White
Write-Host "3. Set Root Directory to: backend" -ForegroundColor White
Write-Host "4. Click 'Deploy Now'" -ForegroundColor White
Write-Host "5. Wait for build to complete" -ForegroundColor White
Write-Host "6. Copy the generated URL" -ForegroundColor White
Write-Host ""
Write-Host "🔗 After deployment, update your GitHub Pages frontend with the Railway URL!" -ForegroundColor Yellow
Write-Host ""

# Wait for user input
Read-Host "Press Enter when deployment is complete to continue..."
