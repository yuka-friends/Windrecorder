# How to add contributions from third-party OCR engines?

1. Fork the project;
2. Create a script for the installation of the OCR engine in the extension folder. After the installation is complete, register it in the config.support_ocr_lst, for details, please refer to the existing scripts;
3. Add an OCR method in windrecorder/ocr_manager.py:
    1. Please add the main function of OCR above the function ocr_image_ms. Its input parameter is the path of the image file, and the return is the string of the recognition result;
    2. If the OCR needs to be initialized, add the initialization status in third_party_ocr_actived_manager, and implement the initialization mechanism under the initialize_third_part_ocr_engine function, and in the main function, it is necessary to add the input parameter force_initialize=False to support forced initialization;
    3. Add the shunt judgment condition of this OCR engine in the ocr_image function;
4. Add the supported languages of the OCR engine in OCR_SUPPORT_CONFIG under windrecorder/const.py;
5. If there is a specific language test set to be added, also add it in OCR_BENCHMARK_TEST_SET under windrecorder/const.py;
6. If the OCR introduces files to the windrecorder program directory, please add the folder to.gitignore to ensure that users can update normally and the binary is not included in the project;
7. That's it! You can submit a PR for us after testing, thank you for your contribution!

### Key technical points

- The name of current chose OCR engine will be stored in config.ocr_engine, please ensure that all names are consistent;
- The recognized languages of the third-party OCR engine are stored in the list config.third_party_engine_ocr_lang. Since it is a list, if the engine supports recognizing multiple languages simultaneously, it can be called from it, if not, call the first item or do not use this configuration;

---

# 如何添加第三方 OCR 引擎贡献？

1. fork 该项目；
2. 在 extension 文件夹下为 OCR 引擎安装创建脚本。安装完毕后注册到 config.support_ocr_lst 中，具体请参见已有脚本；
3. 在 windrecorder/ocr_manager.py 中添加 OCR 方法：
    1. OCR 的主要函数请添加函数 ocr_image_ms 上方。其入参为图片文件路径，返回为识别结果的字符串；
    2. 如果 OCR 需要初始化，请在 third_party_ocr_actived_manager 中添加初始化状态，并且在 initialize_third_part_ocr_engine 函数下实现初始化机制，并在主要函数中需要加入 force_initialize=False 的入参来支持强制初始化；
    3. 在 ocr_image 函数中添加该 OCR 引擎的分流判断条件；
4. 在 windrecorder/const.py 下的 OCR_SUPPORT_CONFIG 添加 OCR 引擎所支持选择的语言；
5. 如果有特定的语言测试集需要加入，同样添加在  windrecorder/const.py 的 OCR_BENCHMARK_TEST_SET 中；
6. 如果 OCR 引入文件到了 windrecorder 程序目录，请将文件夹添加到 .gitignore，以保证用户可以正常更新、且 binary 不被包含在项目中；
7. 这样就完成了！你可以在测试后为我们提交 PR，谢谢你的贡献！

### 技术要点

- 当前选择的 OCR 引擎名将存储在 config.ocr_engine, 请确保所有名称保持一致；
- 第三方 OCR 引擎识别语言以列表形式存储在 config.third_party_engine_ocr_lang 中。由于是列表，如果引擎支持同时识别多种语言可以从中调用，若无，请调用第一项或不适用该配置；