<#
 CrisisLink - apply additive migrations 06, 07, 08 (Windows PowerShell)
 1. asks for an ADMIN MySQL account (migrations need ALTER/CREATE; this is NOT the app account)
 2. takes a backup with mysqldump  -> database\backups\
 3. applies 06, 07, 08 in order and stops on the first error
 Re-runnable: the scripts only add what is missing.
 Usage (from the project root):   powershell -ExecutionPolicy Bypass -File database\apply_migrations.ps1
#>
param(
    [string]$Database = $(if ($env:MYSQL_DATABASE) { $env:MYSQL_DATABASE } else { 'crisislink_db' }),
    [string]$HostName = $(if ($env:MYSQL_HOST) { $env:MYSQL_HOST } else { 'localhost' }),
    [int]$Port = $(if ($env:MYSQL_PORT) { [int]$env:MYSQL_PORT } else { 3306 })
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

foreach ($tool in 'mysql', 'mysqldump') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool was not found on PATH. Add MySQL's bin folder (e.g. C:\Program Files\MySQL\MySQL Server 8.0\bin) to PATH."
    }
}

$adminUser = Read-Host 'MySQL ADMIN user (e.g. root)'
$secure    = Read-Host 'Password' -AsSecureString
$bstr      = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$env:MYSQL_PWD = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)   # lives only in this process
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

try {
    $conn = @("--host=$HostName", "--port=$Port", "--user=$adminUser")

    Write-Host "Checking connection and MySQL version..."
    & mysql @conn --database=$Database -e "SELECT VERSION() AS mysql_version, DATABASE() AS db;"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot connect. Check user/password/database name.' }

    # --result-file avoids PowerShell's UTF-16 redirection problem
    $stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backup = Join-Path $here "backups\pre_migration_$stamp.sql"
    Write-Host "Backing up to $backup ..."
    & mysqldump @conn --single-transaction --routines --triggers --events --result-file="$backup" $Database
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $backup) -or (Get-Item $backup).Length -lt 1000) {
        throw 'Backup failed or is suspiciously small - migrations NOT applied.'
    }
    Write-Host "Backup OK ($([math]::Round((Get-Item $backup).Length/1KB)) KB)." -ForegroundColor Green

    foreach ($f in '06_additive_schema.sql', '07_hierarchy_and_coordinator_data.sql', '08_advanced_routines.sql') {
        $path = (Join-Path $here "migrations\$f") -replace '\\', '/'
        Write-Host "Applying $f ..."
        & mysql @conn --database=$Database -e "source $path"
        if ($LASTEXITCODE -ne 0) { throw "$f failed. Nothing further was applied. Restore with the backup if needed (see database\BACKUP_AND_ROLLBACK.md)." }
    }
    Write-Host 'All migrations applied.' -ForegroundColor Green
}
finally {
    Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
}
