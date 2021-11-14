# NUS_ISS_PLP_PracticeModule_Group13

This is a project to predict video timestamp and sentiment value for YouTube comments.

### Prerequisite:
- Python 3.7
- Google Cloud Api Token for YouTube Data API v3

### Steps:
1. Download zip from [GitHub: NUS_ISS_PLP_PracticeModule_Group13](https://github.com/brooksky/NUS_ISS_PLP_PracticeModule_Group13) and unzip it.
2. Go to *scripts* folder, run *create_venv.bat* to create a Python virtual environment at the root of the project and install required packages.
3. Run *run_flask.bat* to launch the *backend app* to expose API for Chrome Extension app locally.
4. In Chrome browser, open *Manage Extensions* and toggle *Developer mode*.
5. Click on *Load unpacked* button and open *chrome_extension* folder in project. You will see a newly installed Chrome Extension named *PLP Practice Module Group 13*. Turn on this Chrome Extension if Chrome doesn't do so by default.
6. Go to any YouTube video page, switch video to  *Theater Mode*, and then click on brown button from the installed Chrome Extension to start the app for current page.