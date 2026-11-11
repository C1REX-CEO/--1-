@echo off
setlocal
if not exist build mkdir build
if "%VSINSTALLDIR%"=="" call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" -vcvars_ver=14.44
if errorlevel 1 exit /b 1
if "%1"=="cuda" goto cuda
if "%1"=="mpi" goto mpi
if "%1"=="serial" goto serial
for %%W in (1 2 3 4 8 16) do (
  cl /nologo /O2 /EHsc /std:c++17 /D_CRT_SECURE_NO_WARNINGS /DVECTOR_WIDTH=%%W lab5_simd\main.cpp lab5_simd\CS149intrin.cpp lab5_simd\logger.cpp /Fo:build\ /Fe:build\myexp_%%W.exe
  if errorlevel 1 exit /b 1
)
exit /b 0
:cuda
if "%CUDA_PATH%"=="" set "CUDA_PATH=%~dp0..\.lab-tools\cuda"
"%CUDA_PATH%\bin\nvcc.exe" -O2 -std=c++17 -arch=sm_86 lab4_cuda\main.cu -o build\matrix_cuda.exe
exit /b %errorlevel%
:mpi
if "%MSMPI_INC%"=="" set "MSMPI_INC=%~dp0..\.lab-tools\mpi-sdk\PFiles\Microsoft SDKs\MPI\Include"
if "%MSMPI_LIB64%"=="" set "MSMPI_LIB64=%~dp0..\.lab-tools\mpi-sdk\PFiles\Microsoft SDKs\MPI\Lib\x64"
cl /nologo /O2 /EHsc /std:c++17 /I"%MSMPI_INC%" lab3_mpi\main.cpp /Fo:build\ /Fe:build\matrix_mpi.exe /link /LIBPATH:"%MSMPI_LIB64%" msmpi.lib
exit /b %errorlevel%
:serial
cl /nologo /O2 /EHsc /std:c++17 lab3_mpi\serial.cpp /Fo:build\ /Fe:build\matrix_serial.exe
exit /b %errorlevel%
