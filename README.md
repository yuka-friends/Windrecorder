# Windrecorder
A Rewind’s alternative for Windows platform
It runs entirely locally, does not require an internet connection, and does not upload your personal data anywhere.

**NOTE: This project is still under development and the availability of many features is not guaranteed.**
Project Status: have very basic functions


Todo:
- [x] Continuously record screen with smaller file size.
- [x] Extract unchanging frames in the file and ocr record them to the database.
- [x] Provide basic webui for querying and updating database.
- [ ] 🤔

# QuickStart
- Get ffmpeg.exe and place under Windrecorder folder.
- Install dependencies: `pip install -r requirements.txt`
- Starting recording screen: `Python recordScreen.py`
  - **NOTE:** This function is crude and can only be run and terminated manually at present. Before recording, you need to adjust your screen resolution and block recording time in config.json, currently the default is 3840x2160, 60 seconds.
- Query and update database through webui: `python -m streamlit run webui.py`
