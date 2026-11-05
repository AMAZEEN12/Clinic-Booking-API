# Replaces ALL slots (about 3 months of weekdays) and deletes ALL bookings.
# Run from the clinic-booking-api folder, with your Python venv active:
#   $env:API_URL = "https://clinic-booking-api-ayhl.onrender.com"
#   $env:API_KEY = "your-api-key"
#   .\scripts\reseed.ps1 90
param([int]$Days = 90)

if (-not $env:API_KEY -or -not $env:API_URL) {
    Write-Error "Set API_URL and API_KEY first (see the top of this file)."
    exit 1
}

$answer = Read-Host "This DELETES ALL BOOKINGS and replaces every slot. Type RESET to continue"
if ($answer -ne "RESET") {
    Write-Host "Cancelled. Nothing was changed."
    exit 0
}

$body = (python scripts/make_slots.py $Days) -join "`n"
$result = Invoke-RestMethod -Method Post -Uri "$($env:API_URL.TrimEnd('/'))/reset" -Headers @{ "X-API-Key" = $env:API_KEY } -ContentType "application/json" -Body $body
Write-Host "Done. Slots now stored: $($result.slots)"