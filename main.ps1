$python = Get-Content $PSScriptRoot\config\python_path.txt
$main = "$PSScriptRoot\main.py"
& $python $main 

while ($true){
    Start-Sleep -Seconds 100
}
