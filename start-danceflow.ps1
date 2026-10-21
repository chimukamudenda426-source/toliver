$securePassword = Read-Host "Create the organizer dashboard password (at least 12 characters)" -AsSecureString
if ($securePassword.Length -lt 12) {
    throw "The dashboard password must be at least 12 characters long."
}

$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $env:DANCEFLOW_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}

Push-Location $PSScriptRoot
try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.9 -c "import sys; print(sys.version.split()[0])"
        if ($LASTEXITCODE -ne 0) {
            throw "Python 3.9 or newer is required. Install it and try again."
        }
        & py -3.9 server.py
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw "Python 3.9 or newer is required."
        }
        & python server.py
    }
    else {
        throw "Python 3 is required. Install Python 3.9 or later and try again."
    }
}
finally {
    Remove-Item Env:DANCEFLOW_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Pop-Location
}
