$python_path = "$PSScriptRoot\config\python_path.txt"
if (!(Test-Path $python_path)) {
    Write-Output "No python_path.txt found. Running file select script..."
    powershell $PSScriptRoot\setup\select_python.ps1
}

while ($true){
    $python = Get-Content $PSScriptRoot\config\python_path.txt
    if ($python -eq $null -or !(Test-Path $python)) {
        Write-Output "Invalid path in python.txt. Running file select script..."
        powershell $PSScriptRoot\setup\select_python.ps1
    } else {
        break
    }
}

$main = "$PSScriptRoot\main.py"
& $python $main 

while ($true){
    Start-Sleep -Seconds 100
}
