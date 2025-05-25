# 📱 Telegram Account Checker
Enhanced version of bellingcat's Telegram Phone Checker!

A Python script to check Telegram accounts using phone numbers or usernames, now with more detailed user 
information and enhanced status display.

## ✨ Features

- 🔍 Check single or multiple phone numbers and usernames.
- 📁 Import numbers and usernames from text files.
- 📸 Auto-download all profile pictures for a user.
- 💾 Save results as detailed JSON files.
- 🔐 Secure credential storage (API ID, hash, and phone number in `config.pkl`).
- 📊 Detailed user information, including:
    - Basic info: ID, username, first/last name, phone.
    - Account status: Premium, Verified, Bot, Fake.
    - Enhanced last seen status: Online, Offline (with exact timestamp), Recently, Last Week, Last Month,
      or Unavailable, nothing if privacy is restricted.
    - Profile details: Bio, common chats count.
    - Interaction status: Blocked by user.
- 📝 Logging of operations to `telegram_checker.log`.
- 🎨 Rich console output for better readability and interaction.
- 💨 Option to clear saved credentials and session.

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
1. Check phone numbers from input
2. Check phone numbers from file
3. Check usernames from input
4. Check usernames from file
5. Clear saved credentials
6. Exit

## 📂 Output

Results are saved in:
- `results/` - JSON files with detailed information
- `profile_photos/` - Downloaded profile pictures

## 📊 Result EXAMPLE

The script provides both a summary in the console and detailed JSON output.

**Enhanced Results Summary (Console Output Example):**
```text
Enhanced Results Summary:
✓ +12345678900: John Doe (@johndoe_example)
  📅 Exact time: 2025-05-25 10:30:45 UTC
  📝 Bio: Just an example bio here. Living the example life! Follow for more examples...
  ⭐ Telegram Premium user
  ✅ Verified account
  👥 Common chats: 2
  📸 Profile photos downloaded: 2

✓ example_user: Jane Smith (@example_user)
  📅 Status: Last seen recently (1 second - 3 days ago) [yellow](Privacy restricted - exact time hidden)[/yellow]
  📝 Bio: Exploring the digital world.
  🚫 User has blocked you
  📸 Profile photos downloaded: 1

❌ +98765432100: No Telegram account found
```

**Detailed Results (JSON Output Example - content of `results/results_YYYYMMDD_HHMMSS.json`):**
```json
{
  "+12345678900": {
    "id": 123456789,
    "username": "johndoe_example",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+12345678900",
    "premium": true,
    "verified": true,
    "fake": false,
    "bot": false,
    "last_seen": "Last seen: 2025-05-25 10:30:45 UTC",
    "last_seen_exact": "2025-05-25 10:30:45 UTC",
    "status_type": "offline",
    "bio": "Just an example bio here. Living the example life! Follow for more examples...",
    "common_chats_count": 2,
    "blocked": false,
    "profile_photos": [
      "profile_photos/123456789_+12345678900_photo_0.jpg",
      "profile_photos/123456789_+12345678900_photo_1.jpg"
    ],
    "privacy_restricted": false
  },
  "example_user": {
    "id": 987654321,
    "username": "example_user",
    "first_name": "Jane",
    "last_name": "Smith",
    "phone": "",
    "premium": false,
    "verified": false,
    "fake": false,
    "bot": false,
    "last_seen": "Last seen recently (1 second - 3 days ago)",
    "last_seen_exact": null,
    "status_type": "recently",
    "bio": "Exploring the digital world.",
    "common_chats_count": 0,
    "blocked": true,
    "profile_photos": [
      "profile_photos/987654321_example_user_photo_0.jpg"
    ],
    "privacy_restricted": true
  },
  "+98765432100": {
    "error": "No Telegram account found"
  }
}
```

## ⚠️ Note

This tool is for educational purposes only. Please respect Telegram's terms of service and user privacy.

## 📄 License

MIT License
