# 🦝 Windrecorder - A Rewind’s alternative for Windows

It runs entirely locally, does not require any internet request after deployed, and won't upload your personal data anywhere.

> What's Rewind: https://www.rewind.ai/

![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/preview.png)


**NOTE: This project is still under development and the availability of many features are not guaranteed.**

Project Status: have very basic functions


### Todo:
- [x] Continuously record screen with smaller file size.
- [x] Extract unchanging frames in the file and ocr record them to the database.
- [x] Provide basic webui for querying and updating database.
- [ ] Better webui dashboard & control center
- [ ] Automated operation
- [ ] Fully i18n support
- [ ] 🤔


# 🦝 QuickStart

- Installed ffmpeg and it can be accessed from PATH.

- Install dependencies: `pip install -r requirements.txt`

- Starting recording screen: `Python recordScreen.py` or run `start_record.bat`

  - **NOTE:** This function is crude and can only be run and terminated manually at present. Before recording, you need to adjust your screen resolution and block recording time in `config.json`, currently the default set is 3840x2160, 60 seconds.

- Query and update database through webui: `python -m streamlit run webui.py` or run  `start_webui.bat`

- We recommend using Windows.Media.Ocr.Cli method to OCR Video data, so make sure your Windows computer has installed the corresponding OCR language module (it should have been installed with IME by default). For more information: https://learn.microsoft.com/en-us/windows/powertoys/text-extractor


# 🧡
If you like this project, feel free to check [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) 's healing music on YouTube and Stream music platform <3

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
