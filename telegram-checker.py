import asyncio
import json
import logging
import os
import pickle
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from telethon.sync import TelegramClient, errors
from telethon.tl import types
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.functions.users import GetFullUserRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler("telegram_checker.log"), logging.StreamHandler()])
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
    last_seen_exact: Optional[str] = None
    status_type: Optional[str] = None
    bio: Optional[str] = None
    common_chats_count: Optional[int] = None
    blocked: Optional[bool] = None
    profile_photos: List[str] = None
    privacy_restricted: bool = False

    @classmethod
    async def from_user(cls, client: TelegramClient, user: types.User, phone: str = "") -> 'TelegramUser':
        try:
            bio = ''
            common_chats_count = 0
            blocked = False
            
            try:
                full_user = await client(GetFullUserRequest(user.id))
                user_full_info = full_user.full_user
                bio = getattr(user_full_info, 'about', '') or ''
                common_chats_count = getattr(user_full_info, 'common_chats_count', 0)
                blocked = getattr(user_full_info, 'blocked', False)
            except:
                pass

            status_info = get_enhanced_user_status(user.status)
            
            return cls(
                id=user.id,
                username=user.username,
                first_name=getattr(user, 'first_name', None) or "",
                last_name=getattr(user, 'last_name', None) or "",
                phone=phone,
                premium=getattr(user, 'premium', False),
                verified=getattr(user, 'verified', False),
                fake=getattr(user, 'fake', False),
                bot=getattr(user, 'bot', False),
                last_seen=status_info['display_text'],
                last_seen_exact=status_info['exact_time'],
                status_type=status_info['status_type'],
                bio=bio,
                common_chats_count=common_chats_count,
                blocked=blocked,
                privacy_restricted=status_info['privacy_restricted'],
                profile_photos=[]
            )
        except Exception as e:
            logger.error(f"Error creating TelegramUser: {str(e)}")
            status_info = get_enhanced_user_status(getattr(user, 'status', None))
            return cls(
                id=user.id,
                username=getattr(user, 'username', None),
                first_name=getattr(user, 'first_name', None) or "",
                last_name=getattr(user, 'last_name', None) or "",
                phone=phone,
                premium=getattr(user, 'premium', False),
                verified=getattr(user, 'verified', False),
                fake=getattr(user, 'fake', False),
                bot=getattr(user, 'bot', False),
                last_seen=status_info['display_text'],
                last_seen_exact=status_info['exact_time'],
                status_type=status_info['status_type'],
                privacy_restricted=status_info['privacy_restricted'],
                profile_photos=[]
            )

def get_enhanced_user_status(status: types.TypeUserStatus) -> Dict[str, Any]:
    result = {
        'display_text': 'Unknown',
        'exact_time': None,
        'status_type': 'unknown',
        'privacy_restricted': False
    }
    
    if isinstance(status, types.UserStatusOnline):
        result.update({
            'display_text': "Currently online",
            'status_type': 'online',
            'privacy_restricted': False
        })
    elif isinstance(status, types.UserStatusOffline):
        exact_time = status.was_online.strftime('%Y-%m-%d %H:%M:%S UTC')
        result.update({
            'display_text': f"Last seen: {exact_time}",
            'exact_time': exact_time,
            'status_type': 'offline',
            'privacy_restricted': False
        })
    elif isinstance(status, types.UserStatusRecently):
        result.update({
            'display_text': "Last seen recently (1 second - 3 days ago)",
            'status_type': 'recently',
            'privacy_restricted': True
        })
    elif isinstance(status, types.UserStatusLastWeek):
        result.update({
            'display_text': "Last seen within a week (3-7 days ago)",
            'status_type': 'last_week',
            'privacy_restricted': True
        })
    elif isinstance(status, types.UserStatusLastMonth):
        result.update({
            'display_text': "Last seen within a month (7-30 days ago)",
            'status_type': 'last_month',
            'privacy_restricted': True
        })
    elif status is None:
        result.update({
            'display_text': "Status unavailable",
            'status_type': 'unavailable'
        })
    
    return result

def validate_phone_number(phone: str) -> str:
    phone = re.sub(r'[^\d+]', '', phone.strip())
    if not phone.startswith('+'): phone = '+' + phone
    if not re.match(r'^\+\d{10,15}$', phone): raise ValueError(f"Invalid phone number format: {phone}")
    return phone

def validate_username(username: str) -> str:
    username = username.strip().lstrip('@')
    if not re.match(r'^[A-Za-z]\w{3,30}[A-Za-z0-9]$', username): raise ValueError(f"Invalid username format: {username}")
    return username

class TelegramChecker:
    def __init__(self):
        self.config = self.load_config()
        self.client = None
        PROFILE_PHOTOS_DIR.mkdir(exist_ok=True)
        RESULTS_DIR.mkdir(exist_ok=True)

    def load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'rb') as f: return pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, 'wb') as f: pickle.dump(self.config, f)

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
            if not photos: return
            user_data.profile_photos = []
            for i, photo in enumerate(photos):
                identifier = user_data.phone if user_data.phone else user_data.username
                photo_path = PROFILE_PHOTOS_DIR / f"{user.id}_{identifier}_photo_{i}.jpg"
                await self.client.download_media(photo, file=photo_path)
                user_data.profile_photos.append(str(photo_path))
        except Exception as e:
            logger.error(f"Error downloading profile photos for {user.id}: {str(e)}")

    async def check_phone_number(self, phone: str) -> Optional[TelegramUser]:
        try:
            phone = validate_phone_number(phone)
            try:
                user = await self.client.get_entity(phone)
                telegram_user = await TelegramUser.from_user(self.client, user, phone)
                await self.download_all_profile_photos(user, telegram_user)
                return telegram_user
            except:
                contact = types.InputPhoneContact(client_id=0, phone=phone, first_name="Test", last_name="User")
                result = await self.client(ImportContactsRequest([contact]))
                
                if not result.users: return None
                
                user = result.users[0]
                try:
                    full_user = await self.client.get_entity(user.id)
                    await self.client(DeleteContactsRequest(id=[user.id]))
                    telegram_user = await TelegramUser.from_user(self.client, full_user, phone)
                    await self.download_all_profile_photos(full_user, telegram_user)
                    return telegram_user
                finally:
                    try:
                        await self.client(DeleteContactsRequest(id=[user.id]))
                    except:
                        pass
        except Exception as e:
            logger.error(f"Error checking {phone}: {str(e)}")
            return None

    async def check_username(self, username: str) -> Optional[TelegramUser]:
        try:
            username = validate_username(username)
            user = await self.client.get_entity(username)
            if not isinstance(user, types.User): return None
            telegram_user = await TelegramUser.from_user(self.client, user, "")
            await self.download_all_profile_photos(user, telegram_user)
            return telegram_user
        except ValueError as e:
            logger.error(f"Invalid username {username}: {str(e)}")
            return None
        except errors.UsernameNotOccupiedError:
            logger.error(f"Username {username} not found")
            return None
        except Exception as e:
            logger.error(f"Error checking username {username}: {str(e)}")
            return None

    async def process_phones(self, phones: List[str]) -> dict:
        results = {}
        total_phones = len(phones)
        console.print(f"\n[cyan]Processing {total_phones} phone numbers...[/cyan]")
        
        for i, phone in enumerate(phones, 1):
            try:
                phone = phone.strip()
                if not phone: continue
                console.print(f"[cyan]Checking {phone} ({i}/{total_phones})[/cyan]")
                user = await self.check_phone_number(phone)
                results[phone] = asdict(user) if user else {"error": "No Telegram account found"}
            except ValueError as e:
                results[phone] = {"error": str(e)}
            except Exception as e:
                results[phone] = {"error": f"Unexpected error: {str(e)}"}
        return results

    async def process_usernames(self, usernames: List[str]) -> dict:
        results = {}
        total_usernames = len(usernames)
        console.print(f"\n[cyan]Processing {total_usernames} usernames...[/cyan]")
        
        for i, username in enumerate(usernames, 1):
            try:
                username = username.strip()
                if not username: continue
                console.print(f"[cyan]Checking {username} ({i}/{total_usernames})[/cyan]")
                user = await self.check_username(username)
                results[username] = asdict(user) if user else {"error": "No Telegram account found"}
            except ValueError as e:
                results[username] = {"error": str(e)}
            except Exception as e:
                results[username] = {"error": f"Unexpected error: {str(e)}"}
        return results

def display_enhanced_results(results: dict):
    console.print("\n[bold]Enhanced Results Summary:[/bold]")
    
    for identifier, data in results.items():
        if "error" in data:
            console.print(f"[red]❌ {identifier}: {data['error']}[/red]")
        else:
            name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            username = f"@{data.get('username', 'no username')}"
            
            status_line = f"[green]✓ {identifier}: {name} ({username})[/green]"
            
            if data.get('privacy_restricted'):
                status_line += " [yellow](Privacy restricted - exact time hidden)[/yellow]"
            
            if data.get('last_seen_exact'):
                status_line += f"\n  📅 Exact time: {data['last_seen_exact']}"
            else:
                status_line += f"\n  📅 Status: {data.get('last_seen', 'Unknown')}"
            
            if data.get('bio'):
                status_line += f"\n  📝 Bio: {data['bio'][:100]}{'...' if len(data['bio']) > 100 else ''}"
            
            if data.get('premium'):
                status_line += "\n  ⭐ Telegram Premium user"
            
            if data.get('verified'):
                status_line += "\n  ✅ Verified account"
            
            if data.get('blocked'):
                status_line += "\n  🚫 User has blocked you"
            
            if data.get('common_chats_count', 0) > 0:
                status_line += f"\n  👥 Common chats: {data['common_chats_count']}"
            
            if data.get('profile_photos'):
                status_line += f"\n  📸 Profile photos downloaded: {len(data['profile_photos'])}"
            
            console.print(status_line)
            console.print()

async def main():
    checker = TelegramChecker()
    await checker.initialize()
    
    while True:
        rprint("\n[bold cyan]Telegram Account Checker[/bold cyan]")
        rprint("\n1. Check phone numbers from input")
        rprint("2. Check phone numbers from file")
        rprint("3. Check usernames from input")
        rprint("4. Check usernames from file")
        rprint("5. Clear saved credentials")
        rprint("6. Exit")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5", "6"])
        
        if choice == "1":
            phones = [p.strip() for p in Prompt.ask("Enter phone numbers (comma-separated)").split(",")]
            results = await checker.process_phones(phones)
        elif choice == "2":
            file_path = Prompt.ask("Enter the path to your phone numbers file")
            try:
                with open(file_path, 'r') as f:
                    phones = [line.strip() for line in f if line.strip()]
                results = await checker.process_phones(phones)
            except FileNotFoundError:
                console.print("[red]File not found![/red]")
                continue
        elif choice == "3":
            usernames = [u.strip() for u in Prompt.ask("Enter usernames (comma-separated)").split(",")]
            results = await checker.process_usernames(usernames)
        elif choice == "4":
            file_path = Prompt.ask("Enter the path to your usernames file")
            try:
                with open(file_path, 'r') as f:
                    usernames = [line.strip() for line in f if line.strip()]
                results = await checker.process_usernames(usernames)
            except FileNotFoundError:
                console.print("[red]File not found![/red]")
                continue
        elif choice == "5":
            if Confirm.ask("Are you sure you want to clear saved credentials?"):
                if CONFIG_FILE.exists(): CONFIG_FILE.unlink()
                if Path('telegram_checker_session.session').exists(): Path('telegram_checker_session.session').unlink()
                console.print("[green]Credentials cleared. Please restart the program.[/green]")
                break
            continue
        else:
            break
            
        if 'results' in locals():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RESULTS_DIR / f"results_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            console.print(f"\n[green]Results saved to {output_file}[/green]")
            display_enhanced_results(results)
            
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
