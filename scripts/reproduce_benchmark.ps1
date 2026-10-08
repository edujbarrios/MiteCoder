param(
    [Parameter(Mandatory = $true)]
    [string]$Config,
    [string]$ModelPath,
    [string]$Output = "benchmark-results/reproduction"
)

$ErrorActionPreference = "Stop"
$arguments = @("-m", "mitecoder", "benchmark", "--suite", "microswe", "--config", $Config, "--output", $Output)
if ($ModelPath) {
    $arguments += @("--model-path", $ModelPath)
}

& python @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
