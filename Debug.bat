@echo off
chcp 65001 > nul
echo Mode Debug - Lancement de 4G Monitor...
echo.

REM On force l'utilisation de python console pour voir les erreurs
py 4G_Monitor.pyw

echo.
echo ==========================================
echo L'application s'est fermée.
echo S'il y a une erreur ci-dessus, copiez-la.
echo ==========================================
pause





