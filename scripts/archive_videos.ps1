<#
.Synopsis
Activate the local Python virtual environment for the current PowerShell session,
and run the processor.py script with required kwargs.

.Notes
On Windows, it may be required to enable this Activate.ps1 script by setting the
execution policy for the user. You can do this by issuing the following PowerShell
command:

PS C:\> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

For more information on Execution Policies: 
https://go.microsoft.com/fwlink/?LinkID=135170
#>

Write-Host "Activating local Python virtualenv"
.venv\Scripts\activate.ps1
Write-Host "Uploading processed videos to Azure"
$source_dir = "D:\automated-exports\processed"

python archiver.py source_dir=$source_dir