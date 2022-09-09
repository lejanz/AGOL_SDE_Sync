$python = Get-Content $PSScriptRoot\..\config\python_path.txt

& $python -m pip install --trusted-host files.pythonhosted.org  --trusted-host pypi.python.org --trusted-host pypi.org python-certifi-win32
& $python -m pip install -r $PSScriptRoot\..\requirements.txt

Read-Host -Prompt "Press Enter to exit"