LOST & FOUND PORTAL — WINDOWS SETUP
===================================

REQUIREMENTS
- Windows 10/11
- Python 3.10 or newer
- VS Code recommended (Notepad also works)
- Chrome or another browser

STEP 1: EXTRACT
Right-click the ZIP file and choose "Extract All...".
Choose a simple location such as Desktop\lost_and_found_portal.

STEP 2: INSTALL PYTHON
Install Python from https://www.python.org/downloads/
IMPORTANT: during setup, tick "Add python.exe to PATH".
Open Command Prompt and run:
    py --version
If that does not work, try:
    python --version

STEP 3: OPEN PROJECT FOLDER
Open VS Code, choose File > Open Folder, and select the extracted
lost_and_found_portal folder. Or open the folder in File Explorer,
click the address bar, type cmd, and press Enter.

STEP 4: CREATE A VIRTUAL ENVIRONMENT
In the terminal, make sure you are inside the project folder, then run:
    py -m venv .venv
    .venv\Scripts\activate

If activation is blocked, use Command Prompt (cmd), not PowerShell.
Alternatively, install packages with:
    py -m pip install -r requirements.txt

STEP 5: INSTALL FLASK
    py -m pip install -r requirements.txt

STEP 6: RUN THE WEBSITE
    py app.py

You should see a message that Flask is running on http://127.0.0.1:5000
Keep the terminal open. Open Chrome and visit:
    http://127.0.0.1:5000

STEP 7: TRY IT
1. Click Sign Up and create an account.
2. Click Report Item and submit a Lost or Found report.
3. Return to Home and test search/filter.
4. Open My Reports to resolve or delete your own report.

IMPORTANT
- This is a local development project. It is not yet deployed online.
- Do not use real sensitive personal information in a classroom demo.
- Do not share the Flask development server publicly.
- portal.db is created automatically on first run.
- Uploaded images are saved in static/uploads.
- To stop the server, return to terminal and press Ctrl+C.

TROUBLESHOOTING
"py is not recognized": reinstall Python and tick "Add python.exe to PATH",
then close and reopen the terminal.
"No module named flask": run py -m pip install -r requirements.txt.
"Address already in use": stop the other server or use another port.
Blank page: read the error in the terminal and check that you opened
http://127.0.0.1:5000, not a file by double-clicking index.html.
