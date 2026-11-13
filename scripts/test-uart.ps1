# Run from the repository root after closing Serial Monitor:
# powershell -ExecutionPolicy Bypass -File scripts/test-uart.ps1 -Port COM7
# Only sends PING and deliberately invalid commands. No motor commands.
[CmdletBinding()]
param(
    [string]$Port,
    [ValidateRange(1, 10000)]
    [int]$Count = 100
)

$ErrorActionPreference = 'Stop'
if (-not $Port) {
    $availablePorts = [System.IO.Ports.SerialPort]::GetPortNames()
    Write-Host ('Available ports: ' + ($availablePorts -join ', '))
    throw 'Specify the USB-TTL port with -Port COM7 (replace COM7 with your port). Do not select a Bluetooth port.'
}

$connection = New-Object System.IO.Ports.SerialPort -ArgumentList $Port, 115200, None, 8, One
$connection.NewLine = "`n"
$connection.ReadTimeout = 15000
$connection.WriteTimeout = 2000
$connection.DtrEnable = $false
$connection.RtsEnable = $false
$checks = 0

function Test-Reply {
    param([string]$Expected, [switch]$Prefix)
    try {
        $actual = $connection.ReadLine().TrimEnd([char]13)
    } catch [System.TimeoutException] {
        throw "No UART reply. Expected '$Expected'. Check that STM32 is running (F5), TXD->A10, RXD->A9, GND->GND, and baud=115200."
    }
    if (($Prefix -and -not $actual.StartsWith($Expected, [StringComparison]::Ordinal)) -or
        (-not $Prefix -and $actual -cne $Expected)) {
        throw "UART mismatch: expected '$Expected', received '$actual'."
    }
    $script:checks++
}

try {
    $connection.Open()
    $connection.DiscardInBuffer()
    # Finish any partial frame left by a previous terminal session.
    $connection.Write("`n")
    Start-Sleep -Milliseconds 100
    $connection.DiscardInBuffer()
    Write-Host "Testing $Port at 115200 8N1. First reply may take up to 15 seconds during startup."
    $connection.Write("#start RUBIK PING`n")
    Test-Reply '#start ACK'
    $connection.ReadTimeout = 2000

    for ($i = 1; $i -le $Count; $i++) {
        $connection.Write("#p$i RUBIK PING`n")
        Test-Reply "#p$i ACK"
    }

    foreach ($ending in @("`r", "`n", "`r`n")) {
        $connection.Write('#ending RUBIK PING' + $ending)
        Test-Reply '#ending ACK'
    }

    $connection.Write('#fragment RUBIK PI')
    Start-Sleep -Milliseconds 30
    $connection.Write("NG`n")
    Test-Reply '#fragment ACK'

    $connection.Write("#bad RUBIK PING extra`n")
    Test-Reply '#bad NACK BAD_CMD unexpected_arguments'
    $connection.Write('#long RUBIK PING ' + ('x' * 120) + "`n")
    Test-Reply '#long NACK BAD_CMD line_too_long'
    $connection.Write("#binary RUBIK PING$([char]0)`n")
    Test-Reply '#binary NACK BAD_CMD invalid_character'
    $connection.Write("#recover RUBIK PING`n")
    Test-Reply '#recover ACK'

    Write-Host "PASS: $checks replies matched (PING, CR/LF/CRLF, fragmented frame, invalid/long frame and recovery)." -ForegroundColor Green
    Write-Host 'This verifies UART communication. It does not verify servo motion.'
} finally {
    if ($connection.IsOpen) { $connection.Close() }
    $connection.Dispose()
}
