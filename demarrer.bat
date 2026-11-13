@echo off
setlocal
title Slovo - Apprendre le russe
cd /d "%~dp0"
if errorlevel 1 goto directory_error

echo.
echo   SLOVO - Votre espace pour apprendre le russe
echo.

if not exist "app.py" goto files_error
if not exist "requirements.txt" goto files_error
if exist ".venv\Scripts\python.exe" goto check_env

echo [1/3] Creation de l'environnement virtuel...
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto create_with_py
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto python_error
python -m venv ".venv"
if errorlevel 1 goto env_error
goto check_env

:create_with_py
py -3 -m venv ".venv"
if errorlevel 1 goto env_error

:check_env
echo [1/3] Verification et activation de l'environnement...
"%~dp0.venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 10) or sys.prefix == sys.base_prefix)" >nul 2>&1
if errorlevel 1 goto env_error
if not exist ".venv\Scripts\activate.bat" goto env_error
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto env_error

echo [2/3] Verification rapide des dependances...
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\check_dependencies.py" >nul 2>&1
if not errorlevel 1 goto launch
"%~dp0.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt" -c "%~dp0requirements.lock"
if errorlevel 1 goto dependencies_error

echo.
:launch
echo [3/3] Lancement de Slovo...
echo.
echo   Ouvrez http://127.0.0.1:5000 dans votre navigateur.
echo   Gardez cette fenetre ouverte pendant l'utilisation.
echo   Pour arreter l'application : Ctrl+C ou fermez cette fenetre.
echo.
set "HOST=127.0.0.1"
set "PORT=5000"
"%~dp0.venv\Scripts\python.exe" "%~dp0serve.py"
if errorlevel 1 goto app_error
exit /b 0

:directory_error
echo ERREUR : Impossible d'acceder au dossier de l'application.
goto failure

:files_error
echo ERREUR : app.py ou requirements.txt est introuvable.
echo Conservez ce fichier BAT dans le dossier de Slovo.
goto failure

:python_error
echo ERREUR : Python 3.10 ou plus recent est necessaire.
echo Installez Python depuis https://www.python.org/downloads/
echo Activez l'option Add Python to PATH, puis relancez ce fichier.
goto failure

:env_error
echo ERREUR : Impossible de creer ou d'utiliser l'environnement .venv.
echo Verifiez votre installation Python et les droits sur ce dossier.
echo Si le projet a ete deplace, renommez .venv en .venv-ancien,
echo puis relancez ce fichier pour recreer l'environnement.
goto failure

:dependencies_error
echo ERREUR : L'installation des dependances a echoue.
echo Verifiez votre connexion Internet et les messages ci-dessus.
goto failure

:app_error
echo.
echo ERREUR : L'application s'est arretee avec une erreur.
echo Consultez le message ci-dessus. Si le port 5000 est occupe,
echo fermez l'autre instance de Slovo avant de relancer.

:failure
echo.
pause
exit /b 1
