# Sospana Sonke - one-click GitHub setup
# Run this by double-clicking "1-SETUP-GITHUB.bat" (which launches this script).
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   Sospana Sonke  -  Put your code on GitHub" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Git installed?
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "[X] Git is not installed. Install it from https://git-scm.com and run this again." -ForegroundColor Red
  return
}

# 2. Make sure git has an identity (only set locally if you don't already have one)
if (-not (git config user.email)) { git config user.email "lungani@sospana-sonke.local" | Out-Null }
if (-not (git config user.name))  { git config user.name  "Lungani Tshabalala"          | Out-Null }

# 3. Create the local repository and commit everything
if (-not (Test-Path ".git")) {
  Write-Host "Creating a local git repository..." -ForegroundColor Gray
  git init | Out-Null
}
git add -A
git commit -m "Sospana Sonke - initial commit" 2>$null | Out-Null
git branch -M main
Write-Host "[OK] Local repository ready." -ForegroundColor Green
Write-Host ""

$pushed = $false

# 4. Best path: GitHub CLI (fully automatic) if it's installed and signed in
if (Get-Command gh -ErrorAction SilentlyContinue) {
  gh auth status 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Creating a PRIVATE GitHub repo and uploading with GitHub CLI..." -ForegroundColor Green
    gh repo create sospana-sonke --private --source . --remote origin --push
    if ($LASTEXITCODE -eq 0) { $pushed = $true }
  }
}

# 5. Fallback: you create an empty repo in the browser, we push to it
if (-not $pushed) {
  Write-Host "We'll create the repository in your browser (you're already logged in)." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "   1. Open this page:  https://github.com/new"
  Write-Host "   2. Repository name:  sospana-sonke"
  Write-Host "   3. You can choose Private. Do NOT tick 'Add a README'."
  Write-Host "   4. Click the green 'Create repository' button."
  Write-Host ""
  $u = Read-Host "Now type your GitHub username and press Enter"
  $u = $u.Trim()
  git remote remove origin 2>$null | Out-Null
  git remote add origin "https://github.com/$u/sospana-sonke.git"
  Write-Host ""
  Write-Host "Uploading... if a 'Sign in to GitHub' window pops up, click Authorize (no typing needed)." -ForegroundColor Green
  git push -u origin main
  if ($LASTEXITCODE -eq 0) {
    $pushed = $true
    Write-Host ""
    Write-Host "[DONE] Your code is on GitHub:  https://github.com/$u/sospana-sonke" -ForegroundColor Green
  } else {
    Write-Host ""
    Write-Host "[!] The upload hit a problem. Copy the red text above and send it to Claude - I'll fix it." -ForegroundColor Red
  }
} else {
  Write-Host ""
  Write-Host "[DONE] Your code is on GitHub in a private repo called 'sospana-sonke'." -ForegroundColor Green
}

Write-Host ""
Write-Host "Next: come back to Claude and we'll put the app online for free (Neon + Render + Vercel)." -ForegroundColor Cyan
Write-Host ""
