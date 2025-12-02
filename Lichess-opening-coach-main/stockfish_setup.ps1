$ErrorActionPreference = "Stop"

$stockfishUrl = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-windows-x86-64-avx2.zip"
$zipPath = "stockfish.zip"
$extractPath = "stockfish_engine"

Write-Host "Downloading Stockfish..."
Invoke-WebRequest -Uri $stockfishUrl -OutFile $zipPath

Write-Host "Extracting Stockfish..."
Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

# Find the executable
$exe = Get-ChildItem -Path $extractPath -Recurse -Filter "stockfish*.exe" | Select-Object -First 1

if ($exe) {
    # Move to root for easier access
    Move-Item -Path $exe.FullName -Destination "stockfish.exe" -Force
    Write-Host "Stockfish installed successfully to $(Get-Location)\stockfish.exe"
} else {
    Write-Error "Could not find Stockfish executable in the extracted files."
}

# Cleanup
Remove-Item $zipPath -Force
Remove-Item $extractPath -Recurse -Force
