# Business Card Image to Contact File(bcimg2cfile)
![](./asset/demo.gif)

## How to use
1. Get API Key
    - Azure Computer Vision API: `./azure`
    - Telegram Bot API: `./telegram`
    - OpenAI API: https://platform.openai.com/api-keys
2. Set API Keys in `./.env`
    ```
    AZURE_KEY=your_computer_vision_key
    TELEGRAM_KEY=your_bot_key
    OPENAI_KEY=your_openai_key
    ```
3. Run the Bot
    ```
    pip install -r requirements.txt
    python main.py
    ```
