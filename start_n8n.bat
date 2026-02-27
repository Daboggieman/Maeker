@echo off
:: Force n8n to include all nodes and use a local folder for configuration
SET "N8N_USER_FOLDER=%CD%\.n8n"
:: Allow access to all files (for local dev only)
SET "N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES=false"
:: Allow access to project directory and root
SET "N8N_RESTRICT_FILE_ACCESS_TO=C:\Users\RAPH-EXT\maker\;C:\"
SET "N8N_BLOCK_NODES="
SET "N8N_NODES_EXCLUDE="
SET "NODES_EXCLUDE=[]"
SET "N8N_NODES_INCLUDE=n8n-nodes-base.executeCommand,n8n-nodes-base.readBinaryFile,n8n-nodes-base.writeBinaryFile"
SET "N8N_PYTHON_EXECUTABLE_PATH=c:\Users\RAPH-EXT\maker\venv\Scripts\python.exe"
SET "N8N_PYTHON_BINARY=c:\Users\RAPH-EXT\maker\venv\Scripts\python.exe"

echo Loading n8n with the following settings:
echo - User Folder: %N8N_USER_FOLDER%
echo - Include Nodes: %N8N_NODES_INCLUDE%
echo - Python Path: %N8N_PYTHON_EXECUTABLE_PATH%

pnpm exec n8n start
pause
