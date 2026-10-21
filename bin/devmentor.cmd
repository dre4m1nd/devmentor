@echo off
setlocal
set "JAR_DIR=%~dp0..\lib"
if not exist "%JAR_DIR%\devmentor.jar" set "JAR_DIR=%USERPROFILE%\.devmentor\lib"
set "JAR_PATH=%JAR_DIR%\devmentor.jar"
if not exist "%JAR_PATH%" (echo [ERROR] Cannot find devmentor.jar & exit /b 1)
set "JAVA_EXE="
if defined DEVMENTOR_JAVA_HOME if exist "%DEVMENTOR_JAVA_HOME%\bin\java.exe" set "JAVA_EXE=%DEVMENTOR_JAVA_HOME%\bin\java.exe"
if not defined JAVA_EXE for /d %%d in ("%USERPROFILE%\.jdks\openjdk-17*" "%USERPROFILE%\.jdks\openjdk-2*") do if exist "%%~d\bin\java.exe" if not defined JAVA_EXE set "JAVA_EXE=%%~d\bin\java.exe"
if not defined JAVA_EXE if defined JAVA_HOME if exist "%JAVA_HOME%\bin\java.exe" set "JAVA_EXE=%JAVA_HOME%\bin\java.exe"
if not defined JAVA_EXE (echo [ERROR] Cannot find Java 17+ & exit /b 2)
"%JAVA_EXE%" -jar "%JAR_PATH%" %*
