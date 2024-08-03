Test machine specifications:

CPU: AMD Ryzen 9 5900X 12-Core Processor 3.70 GHz
RAM: 64GB
GPU: NVIDIA RTX A4000
OS: Windows 11 Pro 23H2

--------------------------------------------------------------------

    Test language: en-US
    Test case: __assets__\OCR_test_1080_en-US.png

    OCR engine               Single image recognition time (sec)    Accuracy
    ---                      ---                                    ---     
    Windows.Media.Ocr.Cli    0.342                                  82.979% 
    ChineseOCR_lite_onnx     0.345                                  72.549% 
    PaddleOCR                2.045                                  90.0%   
    TesseractOCR             1.083                                  100.0%  
    WeChatOCR                0.341                                  100.0%  

--------------------------------------------------------------------

    Test language: zh-Hans-CN
    Test case: __assets__\OCR_test_1080_zh-Hans-CN.png

    OCR engine               Single image recognition time (sec)    Accuracy
    ---                      ---                                    ---     
    Windows.Media.Ocr.Cli    0.262                                  90.206% 
    ChineseOCR_lite_onnx     0.345                                  89.175% 
    PaddleOCR                2.125                                  85.635% 
    TesseractOCR             1.579                                  94.118% 
    WeChatOCR                0.332                                  96.721% 
    
--------------------------------------------------------------------

    Test language: ja-jp
    Test case: __assets__\OCR_test_1080_ja-jp.png

    OCR engine               Single image recognition time (sec)    Accuracy
    ---                      ---                                    ---     
    Windows.Media.Ocr.Cli    Need to be tested                      Need to be tested
    ChineseOCR_lite_onnx     0.347                                  33.333% 
    PaddleOCR                2.048                                  56.383% 
    TesseractOCR             1.558                                  97.253% 
    WeChatOCR                0.342                                  34.432% 
    
--------------------------------------------------------------------