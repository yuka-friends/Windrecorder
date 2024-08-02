# Introduction 介绍

Tesseract OCR is an open-source optical character recognition (OCR) engine, which can recognize more than 100 languages, including Chinese, English, German, French, Italian, etc.

Tesseract OCR 是一款开源的光学字符识别（OCR）引擎，能够识别超过 100 种语言，包括中文、英语、德语、法语、意大利语等

Supported languages: https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files-in-different-versions.md

支持的语言种类：https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files-in-different-versions.md



# How to install 如何安装

1. Download and install the latest installer (tesseract-ocr-w64-setup.exe) here: https://github.com/UB-Mannheim/tesseract/wiki
2. During the installation process, check the required recognition languages in "Additional language data (download)";
3. Copy and note down the installation target path of the program for filling in when configuring Windrecorder later (such as C:\Program Files\Tesseract-OCR);
4. Complete the installation. Open config_tesseract_ocr.bat, paste the copied program installation path, and press Enter to complete the configuration and test.

1. 在此处下载安装最新的安装器（tesseract-ocr-w64-setup.exe）： https://github.com/UB-Mannheim/tesseract/wiki
2. 安装过程中，在 Additional language data(download) 勾选所需的识别语言；
3. 复制记下程序安装目标路径，以便之后在 Windrecorder 配置时填写（如 C:\Program Files\Tesseract-OCR）
4. 完成安装。打开 config_tesseract_ocr.bat，粘贴刚才复制的程序安装路径，回车完成配置与测试；


After the installation is completed, you can switch to use this OCR engine in the settings of Windrecorder.

安装完成后，你可以在 Windrecorder 的设置中切换该 OCR 引擎使用。