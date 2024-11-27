# 📱 Telegram Account Checker
Enhanced version of bellingcat's Telegram Phone Checker!

A Python script to check Telegram accounts using phone numbers.

## ✨ Features

- 🔍 Check single or multiple phone numbers
- 📁 Import numbers from text file
- 📸 Auto-download profile pictures
- 💾 Save results as JSON
- 🔐 Secure credential storage
- 📊 Detailed user information

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/unnohwn/telegram-checker.git
cd telegram-checker
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## 📦 Requirements

Contents of `requirements.txt`:
```
telethon
rich
click
python-dotenv
```

Or install packages individually:
```bash
pip install telethon rich click python-dotenv
```

## ⚙️ Configuration

First time running the script, you'll need:
- Telegram API credentials (get from https://my.telegram.org/apps)
- Your Telegram phone number including countrycode +
- Verification code (sent to your Telegram)

## 💻 Usage

Run the script:
```bash
python telegram_checker.py
```

Choose from options:
1. Check phone numbers directly (comma-separated)
2. Import numbers from text file
3. Clear saved credentials
4. Exit

## 📂 Output

Results are saved in:
- `results/` - JSON files with detailed information
- `profile_photos/` - Downloaded profile pictures

## ⚠️ Note

This tool is for educational purposes only. Please respect Telegram's terms of service and user privacy.

## 📄 License

MIT License
