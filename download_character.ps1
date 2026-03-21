$url = "https://api.pixellab.ai/mcp/characters/a57a868c-f2c3-4e11-b4db-5f255c9408c4/download"
$outPath = "C:\Users\user\Desktop\BomberX\Assets\Art\Characters\player-bomber.zip"
$headers = @{"Authorization"="Bearer 61d36313-e58e-40ac-9528-8c02a8b93d36"}

while ($true) {
    try {
        Invoke-WebRequest -Uri $url -Headers $headers -OutFile $outPath
        Write-Host "Download complete!"
        break
    } catch [System.Net.WebException] {
        $status = $_.Exception.Response.StatusCode
        if ($status -eq 'Locked' -or [int]$status -eq 423) {
            Write-Host "Animations pending (HTTP 423), waiting 15 seconds..."
            Start-Sleep -Seconds 15
        } else {
            Write-Error "Failed to download: $($_.Exception.Message)"
            break
        }
    } catch {
        Write-Error "Unknown error: $_"
        break
    }
}
