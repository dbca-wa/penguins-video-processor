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
.venv\Scripts\Activate.ps1
Write-Host "Processing videos for upload to website"
$source_dir = "D:\automated-exports"
$transcoded_dir = "D:\automated-exports\transcoded"
$processed_dir = "D:\automated-exports\processed"
$preset_import_file = "C:\penguins-video-processor\penguins_preset.json"

python processor.py source_dir=$source_dir transcoded_dir=$transcoded_dir processed_dir=$processed_dir preset_import_file=$preset_import_file