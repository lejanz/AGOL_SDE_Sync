$python_path = "$PSScriptRoot\..\config\python_path.txt"
if (!(Test-Path $python_path)) {
    Write-Output "No python_path.txt found. Running file select script..."
    powershell $PSScriptRoot\select_python.ps1
}

while ($true){
    $python = Get-Content $PSScriptRoot\..\config\python_path.txt
    if ($python -eq $null -or !(Test-Path $python)) {
        Write-Output "Invalid path in python.txt. Running file select script..."
        powershell $PSScriptRoot\select_python.ps1
    } else {
        break
    }
}

& $python -m pip install --trusted-host files.pythonhosted.org  --trusted-host pypi.python.org --trusted-host pypi.org python-certifi-win32
& $python -m pip install -r $PSScriptRoot\..\requirements.txt

Read-Host -Prompt "Press Enter to exit"