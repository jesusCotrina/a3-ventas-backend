<#
.SYNOPSIS
    Levanta la base de datos de Kaudal (Docker, contenedor kaudal_db) y le
    aplica el esquema completo (todas las migraciones de db/migrations/).

.DESCRIPTION
    Pensado tanto para el primer arranque (volumen kaudal_pgdata vacio) como
    para uno posterior. En un volumen nuevo, el arranque automatico de
    Postgres via docker-entrypoint-initdb.d se queda a medias en
    002_empresas_tenant.sql (ver la nota en CLAUDE.md sobre el escape '%%'
    que necesita scripts/migrate.py pero rompe el RAISE de plpgsql via psql
    normal) y el contenedor termina "Exited": este script lo detecta,
    reintenta el arranque (la segunda vez Postgres ya no repite los scripts
    de init, arranca tal cual) y despues aplica TODAS las migraciones
    pendientes con scripts/migrate.py (via psycopg, que si las aplica bien).
    Es idempotente: correrlo de nuevo sobre una base ya al dia no hace nada.

.PARAMETER Seed
    Ademas de aplicar el esquema, siembra datos de ejemplo (usuarios de
    prueba + catalogos/productos/ventas de la empresa DEMO).

.EXAMPLE
    .\scripts\setup_db.ps1
    .\scripts\setup_db.ps1 -Seed
#>
param(
    [switch]$Seed
)

$ErrorActionPreference = "Stop"
$ContainerName = "kaudal_db"
$BackDir = Resolve-Path "$PSScriptRoot\.."

Set-Location $BackDir

Write-Host "Levantando $ContainerName (docker compose up -d)..."
docker compose up -d | Out-Null

$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    $status = docker inspect -f '{{.State.Status}}' $ContainerName 2>$null
    $health = docker inspect -f '{{.State.Health.Status}}' $ContainerName 2>$null

    if ($health -eq "healthy") {
        $healthy = $true
        break
    }
    if ($status -eq "exited") {
        Write-Host "El contenedor se detuvo (normal en un volumen nuevo, ver CLAUDE.md); reintentando..."
        docker compose up -d | Out-Null
    }
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    Write-Error "La base de datos no llego a 'healthy'. Revisa: docker logs $ContainerName"
    exit 1
}

Write-Host "Aplicando migraciones pendientes..."
& "$BackDir\.venv\Scripts\python.exe" "$BackDir\scripts\migrate.py"

if ($Seed) {
    Write-Host "Sembrando datos de ejemplo..."
    & "$BackDir\.venv\Scripts\python.exe" "$BackDir\scripts\seed_test_users.py"
    & "$BackDir\.venv\Scripts\python.exe" "$BackDir\scripts\seed_inventario_demo.py"
}

Write-Host "Listo: base de datos de Kaudal al dia en localhost:5433."
