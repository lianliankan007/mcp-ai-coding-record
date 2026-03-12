$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\\Scripts\\python.exe"

if (-not (Test-Path $python)) {
    throw "Virtual environment not found at $python"
}

Push-Location $root
try {
    & $python -m memory_mcp_server.main
}
finally {
    Pop-Location
}
