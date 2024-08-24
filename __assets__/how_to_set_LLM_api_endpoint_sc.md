# 入门指南：如何配置大语言模型服务

### 大语言模型（LLM）是什么？

大语言模型是一种基于机器学习的人工智能技术，它可以理解和生成人类语言。大语言模型可以用于各种应用，包括自然语言处理、机器翻译、语音识别、文本生成、对话系统等。ChatGPT 等对话机器人都是基于 LLM 的应用。

### 有哪些云端与本地的大语言模型可以使用？

为了使用这些语言模型服务，你需要获取它们的 API key。（一种类似于密钥的字符串,用于验证和授权对特定API（应用程序编程接口）的访问。）

对于 Windrecorder 所支持的 OpenAI endpoint 格式，需要填入三个信息：

1. base url：服务方提供的 API 地址，例如 `https://api.openai.com/v1`
2. api key：服务方提供的 API key，可能需要开通申请获得，例如 `sk-AbCdEfGxXXXXXXXXXXXXXXXXX`
3. modelname：服务方提供的模型名称，例如 `gpt-4o`。推荐使用有更大上下文窗口的模型，比如 128k 或以上。

这些信息通常可以在服务方的文档中找到。以下是一些常见的模型提供商：

> [!WARNING]
> 当使用云服务时，你的部分数据可能会经由网络被传出。
- 基于云服务：

    1. [OpenAI Platform](https://platform.openai.com/docs/introduction)
        - base url: `https://api.openai.com/v1`
        - modelname: `gpt-4o`
    2. [DeepSeek](https://platform.deepseek.com/)：具有便宜的价格、较为优质的模型，对于色情与政治内容审查可能较为严格；
        - base url: `https://api.deepseek.com/v1`
        - modelname: `deepseek-chat`
    3. [Groq](https://console.groq.com/docs/openai)：提供价格便宜、推理生成速度极快的开源模型；
        - base url: `https://api.groq.com/openai/v1`
        - modelname: `llama-3.1-70b-versatile`
    4. 其他任何兼容 OpenAI 接口的模型服务提供商。欢迎补充。

- 基于本地：
    1. [LM studio](https://lmstudio.ai/)：可以便利地从 hugging face 下载模型在本地运行，通过 `Local Server` 模式提供 api 给本地或局域网内用户调用，从而最大程度保护隐私不被泄露。不过，**本地开源模型通常在智能程度和指令遵循水平较低、生成结果不一定可用**，具体可能需要进行选择与测试；
        - base url: `http://localhost:1234/v1`
        - modelname: `cognitivecomputations/dolphin-2.9-llama3-8b-gguf`
        - api key: `lm-studio`
    2. 其他任何兼容 OpenAI 接口格式的模型服务。如果你有一台运行开源/私有模型的内网服务器、边缘计算设备，均可以通过此接入；
