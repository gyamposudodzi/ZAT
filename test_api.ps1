$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Convert-ToJsonBody {
    param($Body)
    if ($null -eq $Body) {
        return $null
    }
    return ($Body | ConvertTo-Json -Depth 10)
}

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Token,
        $Body,
        [int[]]$ExpectedStatus = @(200)
    )

    $headers = @{}
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }

    $uri = "$baseUrl$Path"
    $jsonBody = Convert-ToJsonBody -Body $Body

    try {
        if ($null -ne $jsonBody) {
            $response = Invoke-WebRequest -Method $Method -Uri $uri -Headers $headers -ContentType "application/json" -Body $jsonBody
        } else {
            $response = Invoke-WebRequest -Method $Method -Uri $uri -Headers $headers
        }

        $statusCode = [int]$response.StatusCode
        $payload = if ($response.Content) { $response.Content | ConvertFrom-Json } else { $null }
    }
    catch {
        if ($null -eq $_.Exception.Response) {
            throw "Could not reach $uri. Start the backend first with .\start_backend.ps1"
        }
        $statusCode = [int]$_.Exception.Response.StatusCode
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $content = $reader.ReadToEnd()
        $reader.Close()
        $payload = if ($content) { $content | ConvertFrom-Json } else { $null }
    }

    if ($ExpectedStatus -notcontains $statusCode) {
        throw "Unexpected status code for $Method $Path. Expected [$($ExpectedStatus -join ', ')], got $statusCode. Payload: $($payload | ConvertTo-Json -Depth 10)"
    }

    [PSCustomObject]@{
        StatusCode = $statusCode
        Payload = $payload
    }
}

Write-Step "Health Check"
$health = Invoke-Api -Method "GET" -Path "/health"
Write-Host ($health.Payload | ConvertTo-Json -Depth 10)

Write-Step "OpenAPI Document"
$openapi = Invoke-Api -Method "GET" -Path "/openapi.json"
Write-Host "OpenAPI version: $($openapi.Payload.openapi)"

Write-Step "Viewer Access"
$viewerSummary = Invoke-Api -Method "GET" -Path "/dashboard/summary" -Token "viewer-token"
Write-Host "Viewer can read summary. Net balance: $($viewerSummary.Payload.data.net_balance)"
$viewerDenied = Invoke-Api -Method "GET" -Path "/records" -Token "viewer-token" -ExpectedStatus @(403)
Write-Host "Viewer records access denied: $($viewerDenied.Payload.error)"

Write-Step "Analyst Access"
$analystRecords = Invoke-Api -Method "GET" -Path "/records?type=income&limit=2&sort_by=amount&sort_direction=asc" -Token "analyst-token"
Write-Host ($analystRecords.Payload | ConvertTo-Json -Depth 10)

Write-Step "Admin Creates User"
$newUser = Invoke-Api -Method "POST" -Path "/users" -Token "admin-token" -Body @{
    name = "QA Reviewer"
    email = "qa.reviewer@finance.local"
    role = "analyst"
    status = "active"
} -ExpectedStatus @(201)
$userId = $newUser.Payload.data.id
Write-Host "Created user ID: $userId"

$userDetail = Invoke-Api -Method "GET" -Path "/users/$userId" -Token "admin-token"
Write-Host ($userDetail.Payload | ConvertTo-Json -Depth 10)

$updatedUser = Invoke-Api -Method "PATCH" -Path "/users/$userId" -Token "admin-token" -Body @{
    role = "viewer"
} -ExpectedStatus @(200)
Write-Host "Updated user role to: $($updatedUser.Payload.data.role)"

Write-Step "Admin Creates, Updates, And Soft Deletes Record"
$newRecord = Invoke-Api -Method "POST" -Path "/records" -Token "admin-token" -Body @{
    amount = 2750
    type = "expense"
    category = "Operations"
    record_date = "2026-04-05"
    notes = "Assessment demo expense"
} -ExpectedStatus @(201)
$recordId = $newRecord.Payload.data.id
Write-Host "Created record ID: $recordId"

$recordDetail = Invoke-Api -Method "GET" -Path "/records/$recordId" -Token "analyst-token"
Write-Host ($recordDetail.Payload | ConvertTo-Json -Depth 10)

$updatedRecord = Invoke-Api -Method "PATCH" -Path "/records/$recordId" -Token "admin-token" -Body @{
    amount = 2600
    notes = "Adjusted assessment demo expense"
} -ExpectedStatus @(200)
Write-Host ($updatedRecord.Payload | ConvertTo-Json -Depth 10)

$deletedRecord = Invoke-Api -Method "DELETE" -Path "/records/$recordId" -Token "admin-token"
Write-Host ($deletedRecord.Payload | ConvertTo-Json -Depth 10)

$missingRecord = Invoke-Api -Method "GET" -Path "/records/$recordId" -Token "analyst-token" -ExpectedStatus @(404)
Write-Host "Deleted record is no longer returned: $($missingRecord.Payload.error)"

Write-Step "Validation And Access Errors"
$invalidRecord = Invoke-Api -Method "POST" -Path "/records" -Token "admin-token" -Body @{
    amount = -50
    type = "income"
    category = "Invalid"
    record_date = "2026-04-05"
} -ExpectedStatus @(400)
Write-Host "Invalid payload rejected: $($invalidRecord.Payload.error)"

$inactiveUser = Invoke-Api -Method "GET" -Path "/dashboard/summary" -Token "inactive-token" -ExpectedStatus @(403)
Write-Host "Inactive user blocked: $($inactiveUser.Payload.error)"

$badSort = Invoke-Api -Method "GET" -Path "/records?sort_by=bogus" -Token "analyst-token" -ExpectedStatus @(400)
Write-Host "Bad sort rejected: $($badSort.Payload.error)"

Write-Step "All API Checks Passed"
Write-Host "The backend responded correctly for health, docs, RBAC, CRUD, filtering, validation, and soft delete." -ForegroundColor Green
