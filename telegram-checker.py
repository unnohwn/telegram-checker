import asyncio
import json
import logging
import os
import pickle
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import re

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from telethon.sync import TelegramClient, errors
from telethon.tl import types
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("telegram_checker.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
console = Console()
CONFIG_FILE = Path("config.pkl")
PROFILE_PHOTOS_DIR = Path("profile_photos")
RESULTS_DIR = Path("results")

@dataclass
class TelegramUser:
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: str
    premium: bool
    verified: bool
    fake: bool
    bot: bool
    last_seen: str
    profile_photos: List[str] = None

    @classmethod
    def from_user(cls, user: types.User, phone: str) -> 'TelegramUser':
        return cls(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=phone,
            premium=user.premium,
            verified=user.verified,
            fake=user.fake,
            bot=user.bot,
            last_seen=get_user_status(user.status),
            profile_photos=[]
        )

def get_user_status(status: types.TypeUserStatus) -> str:
    if isinstance(status, types.UserStatusOnline):
        return "Currently online"
    elif isinstance(status, types.UserStatusOffline):
        return f"Last seen: {status.was_online.strftime('%Y-%m-%d %H:%M:%S')}"
    elif isinstance(status, types.UserStatusRecently):
        return "Last seen recently"
    elif isinstance(status, types.UserStatusLastWeek):
        return "Last seen last week"
    elif isinstance(status, types.UserStatusLastMonth):
        return "Last seen last month"
    return "Unknown"

def validate_phone_number(phone: str) -> str:
    phone = re.sub(r'[^\d+]', '', phone.strip())
    if not phone.startswith('+'):
        phone = '+' + phone
    if not re.match(r'^\+\d{10,15}$', phone):
        raise ValueError(f"Invalid phone number format: {phone}")
    return phone

class TelegramChecker:
    def __init__(self):
        self.config = self.load_config()
        self.client = None
        PROFILE_PHOTOS_DIR.mkdir(exist_ok=True)
        RESULTS_DIR.mkdir(exist_ok=True)

    def load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, 'wb') as f:
            pickle.dump(self.config, f)

    async def initialize(self):
        if not self.config.get('api_id'):
            console.print("[yellow]First time setup - please enter your Telegram API credentials[/yellow]")
            console.print("[cyan]You can get these from https://my.telegram.org/apps[/cyan]")
            self.config['api_id'] = int(Prompt.ask("Enter your API ID"))
            self.config['api_hash'] = Prompt.ask("Enter your API hash", password=True)
            self.config['phone'] = validate_phone_number(Prompt.ask("Enter your phone number (with country code)"))
            self.save_config()

        self.client = TelegramClient('telegram_checker_session', self.config['api_id'], self.config['api_hash'])
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.config['phone'])
            code = Prompt.ask("Enter the verification code sent to your Telegram")
            try:
                await self.client.sign_in(self.config['phone'], code)
            except errors.SessionPasswordNeededError:
                password = Prompt.ask("Enter your 2FA password", password=True)
                await self.client.sign_in(password=password)

    async def download_all_profile_photos(self, user: types.User, user_data: TelegramUser):
        try:
            photos = await self.client.get_profile_photos(user)
            if not photos:
                return

            user_data.profile_photos = []
            for i, photo in enumerate(photos):
                photo_path = PROFILE_PHOTOS_DIR / f"{user.id}_{user_data.phone}_photo_{i}.jpg"
                await self.client.download_media(photo, file=photo_path)
                user_data.profile_photos.append(str(photo_path))
        except Exception as e:
            logger.error(f"Error downloading profile photos for {user.id}: {str(e)}")

    async def check_phone_number(self, phone: str) -> Optional[TelegramUser]:
        try:
            phone = validate_phone_number(phone)
            contact = types.InputPhoneContact(client_id=0, phone=phone, first_name="", last_name="")
            result = await self.client(ImportContactsRequest([contact]))
            
            if not result.users:
                return None
            
            user = result.users[0]
            await self.client(DeleteContactsRequest(id=[user.id]))
            telegram_user = TelegramUser.from_user(user, phone)
            await self.download_all_profile_photos(user, telegram_user)
            return telegram_user
        except Exception as e:
            logger.error(f"Error checking {phone}: {str(e)}")
            return None

    async def process_phones(self, phones: List[str]) -> dict:
        results = {}
        total_phones = len(phones)
        console.print(f"\n[cyan]Processing {total_phones} phone numbers...[/cyan]")
        
        for i, phone in enumerate(phones, 1):
            try:
                phone = phone.strip()
                if not phone:
                    continue
                console.print(f"[cyan]Checking {phone} ({i}/{total_phones})[/cyan]")
                user = await self.check_phone_number(phone)
                results[phone] = asdict(user) if user else {"error": "No Telegram account found"}
            except ValueError as e:
                results[phone] = {"error": str(e)}
            except Exception as e:
                results[phone] = {"error": f"Unexpected error: {str(e)}"}
        return results

async def main():
    checker = TelegramChecker()
    await checker.initialize()
    
    while True:
        rprint("\n[bold cyan]Telegram Account Checker[/bold cyan]")
        rprint("\n1. Check phone numbers from input")
        rprint("2. Check phone numbers from file")
        rprint("3. Clear saved credentials")
        rprint("4. Exit")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4"])
        
        if choice == "1":
            phones = [p.strip() for p in Prompt.ask("Enter phone numbers (comma-separated)").split(",")]
        elif choice == "2":
            file_path = Prompt.ask("Enter the path to your phone numbers file")
            try:
                with open(file_path, 'r') as f:
                    phones = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                console.print("[red]File not found![/red]")
                continue
        elif choice == "3":
            if Confirm.ask("Are you sure you want to clear saved credentials?"):
                if CONFIG_FILE.exists():
                    CONFIG_FILE.unlink()
                if Path('telegram_checker_session.session').exists():
                    Path('telegram_checker_session.session').unlink()
                console.print("[green]Credentials cleared. Please restart the program.[/green]")
                break
            continue
        else:
            break
            
        results = await checker.process_phones(phones)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RESULTS_DIR / f"results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        console.print(f"\n[green]Results saved to {output_file}[/green]")
        console.print("\n[bold]Results Summary:[/bold]")
        for phone, data in results.items():
            if "error" in data:
                console.print(f"[red]❌ {phone}: {data['error']}[/red]")
            else:
                status = f"[green]✓ {phone}: {data.get('first_name', '')} {data.get('last_name', '')} (@{data.get('username', 'no username')})"
                if data.get('profile_photos'):
                    status += f" - {len(data['profile_photos'])} profile photos downloaded"
                console.print(status + "[/green]")
        
        console.print("\n[bold cyan]Detailed Results (JSON):[/bold cyan]")
        formatted_json = json.dumps(results, indent=2)
        console.print(formatted_json)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Program terminated by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]An error occurred: {str(e)}[/red]")
        logger.exception("Unhandled exception occurred")