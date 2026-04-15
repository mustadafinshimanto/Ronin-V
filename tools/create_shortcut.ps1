$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$HOME\Desktop\Ronin-V.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\run_ronin.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.IconLocation = "shell32.dll,25" # Terminal icon
$Shortcut.Save()
Write-Host "[*] Ronin-V Master Shortcut created on Desktop." -ForegroundColor Cyan
