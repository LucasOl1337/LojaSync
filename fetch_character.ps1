$headers = @{
    "Authorization" = "Bearer 61d36313-e58e-40ac-9528-8c02a8b93d36"
    "Content-Type" = "application/json"
    "Accept" = "application/json, text/event-stream"
}

$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "get_character"
        arguments = @{
            character_id = "a57a868c-f2c3-4e11-b4db-5f255c9408c4"
        }
    }
    id = 1
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "https://api.pixellab.ai/mcp" -Method Post -Headers $headers -Body $body
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Error $_.Exception.Message
}
