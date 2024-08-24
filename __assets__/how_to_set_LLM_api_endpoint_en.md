# Getting Started: How to Configure Large Language Model Services

### What is Large Language Model (LLM)?

Large Language Model is a machine learning-based artificial intelligence technology that can understand and generate human language. Large Language Models can be used in a variety of applications, including natural language processing, machine translation, speech recognition, text generation, dialogue systems, etc. Chatbots such as ChatGPT are all LLM-based applications.

### What cloud and local large language models are available?

In order to use these language model services, you need to obtain their API keys. (A key-like string used to authenticate and authorize access to a specific API (application programming interface).)

For the OpenAI endpoint format supported by Windrecorder, three pieces of information need to be filled in:

1. base url: API address provided by the service provider, such as `https://api.openai.com/v1`

2. api key: API key provided by the service provider, which may require an application, such as `sk-AbCdEfGxXXXXXXXXXXXXXXXXX`

3. modelname: Model name provided by the service provider, such as `gpt-4o`. It is recommended to use a model with a larger context window, such as 128k or more.

This information can usually be found in the service provider's documentation. Here are some common model providers:

> [!WARNING]
> When using cloud services, some of your data may be transferred over the network.

- Based on cloud services:
    1. [OpenAI Platform](https://platform.openai.com/docs/introduction)
        - base url: `https://api.openai.com/v1`
        - modelname: `gpt-4o`
    2. [DeepSeek](https://platform.deepseek.com/): has a low price, relatively high-quality models, but may be more stringent in censoring pornographic and political content;
        - base url: `https://api.deepseek.com/v1`
        - modelname: `deepseek-chat`
    3. [Groq](https://console.groq.com/docs/openai): provides open source models with low prices and extremely fast inference generation speed;
        - base url: `https://api.groq.com/openai/v1`
        - modelname: `llama-3.1-70b-versatile`
    4. Any other OpenAI compatible Model service provider with interface. Feel free to supplement.

- Local:
    1. [LM studio](https://lmstudio.ai/): You can conveniently download the model from hugging face and run it locally, and provide API to local or LAN users through the `Local Server` mode, so as to protect privacy from being leaked to the greatest extent. However, **local open source models are usually low in intelligence and instruction compliance, and the generated results may not be available.** You may need to select and test them;
        - base url: `http://localhost:1234/v1`
        - modelname: `cognitivecomputations/dolphin-2.9-llama3-8b-gguf`
        - api key: `lm-studio`
    2. Any other model service compatible with the OpenAI interface format. If you have an intranet server or edge computing device running an open source/private model, you can access it through this;
