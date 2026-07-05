$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BundledPython = "C:\Users\10007877\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path -LiteralPath $BundledPython) {
  $Python = $BundledPython
} elseif ($env:PYTHON) {
  $Python = $env:PYTHON
} else {
  $Python = "python"
}
$CredentialPath = Join-Path $Root "work\binance_prediction_credentials.json"

Push-Location $Root
try {
  $planJson = & $Python ".\work\update_worldcup_r16_monitor.py"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to prepare monitor plan."
  }

  $plan = $planJson | ConvertFrom-Json
  $due = @($plan.due)
  $fetched = New-Object System.Collections.Generic.List[string]
  $hasEnvCredentials = -not [string]::IsNullOrWhiteSpace($env:BINANCE_API_KEY) -and -not [string]::IsNullOrWhiteSpace($env:BINANCE_API_SECRET)

  if ($due.Count -gt 0 -and $hasEnvCredentials) {
    foreach ($match in $due) {
      $contains = @($match.contains)
      & $Python ".\work\binance_prediction_search_topics.py" `
        --query $match.query `
        --contains $contains `
        --top-k 50 `
        --output $match.output

      if ($LASTEXITCODE -eq 0) {
        [void]$fetched.Add([string]$match.key)
      } else {
        Write-Warning "Binance update failed for $($match.title)."
      }
    }
  } elseif ($due.Count -gt 0 -and (Test-Path -LiteralPath $CredentialPath)) {
    $cred = Get-Content -LiteralPath $CredentialPath -Raw | ConvertFrom-Json
    $keySecure = $cred.apiKeyProtected | ConvertTo-SecureString
    $secretSecure = $cred.apiSecretProtected | ConvertTo-SecureString
    $bstr1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($keySecure)
    $bstr2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secretSecure)

    try {
      $env:BINANCE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringUni($bstr1)
      $env:BINANCE_API_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringUni($bstr2)

      foreach ($match in $due) {
        $contains = @($match.contains)
        & $Python ".\work\binance_prediction_search_topics.py" `
          --query $match.query `
          --contains $contains `
          --top-k 50 `
          --output $match.output

        if ($LASTEXITCODE -eq 0) {
          [void]$fetched.Add([string]$match.key)
        } else {
          Write-Warning "Binance update failed for $($match.title)."
        }
      }
    } finally {
      if ($bstr1 -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr1) }
      if ($bstr2 -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr2) }
      Remove-Item Env:\BINANCE_API_KEY -ErrorAction SilentlyContinue
      Remove-Item Env:\BINANCE_API_SECRET -ErrorAction SilentlyContinue
    }
  } elseif ($due.Count -gt 0) {
    Write-Warning "Binance credentials are missing; updated score/status only."
  }

  if ($fetched.Count -gt 0) {
    & $Python ".\work\update_worldcup_r16_monitor.py" --mark-odds @($fetched.ToArray())
    if ($LASTEXITCODE -ne 0) {
      throw "Failed to mark odds update."
    }
  }

  & $Python ".\work\build_worldcup_r16_tabs_site.py"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to rebuild public site."
  }

  Write-Output "monitor_plan_due=$($due.Count)"
  Write-Output "binance_fetched=$($fetched.Count)"
  Write-Output "public_site=$Root\site-canada-morocco\public\index.html"
} finally {
  Pop-Location
}
