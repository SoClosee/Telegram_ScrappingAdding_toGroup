import os
import json
import csv
import time
import random
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest, GetHistoryRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser, UserStatusRecently, UserStatusOnline, UserStatusOffline, PeerChannel
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError
from telethon.tl.functions.channels import InviteToChannelRequest, GetFullChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from colorama import Fore, Style
import sqlite3
import threading

# Load configuration
config_file = 'config.json'
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
else:
    config = {
        "accounts": [],
        "proxies": []
    }

# Save configuration
def save_config():
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

# Connect a new account
def connect_new_account():
    method = input("Enter '1' to use API ID and hash, '2' to enter phone number: ")
    if method == '1':
        api_id = input('Enter API ID: ')
        api_hash = input('Enter API Hash: ')
        phone = input('Enter phone number: ')
        client = TelegramClient(phone, api_id, api_hash)
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            client.sign_in(phone, input('📱 Enter the code: '))
        config['accounts'].append({
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "blacklisted": False,
            "blacklist_time": None
        })
        save_config()
        return f'✅ Account {phone} connected successfully.\n'

    elif method == '2':
        phone = input('Enter phone number: ')
        api_id = input('Enter API ID: ')
        api_hash = input('Enter API Hash: ')
        client = TelegramClient(phone, api_id, api_hash)
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input('📱 Enter the code: ')
            client.sign_in(phone, code)
        config['accounts'].append({
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "blacklisted": False,
            "blacklist_time": None
        })
        save_config()
        return f'✅ Account {phone} connected successfully.\n'
    else:
        return "❌ Invalid choice"

# List connected accounts
def list_connected_accounts():
    if not config['accounts']:
        return "📋 0 connected accounts.\n"
    else:
        response = ""
        for idx, account in enumerate(config['accounts']):
            status = "🔴 Blacklisted" if account['blacklisted'] else "🟢 Active"
            response += f"{idx + 1}. {account['phone']} - {status}\n"
        return response

# Delete a connected account
def delete_connected_account():
    accounts_list = list_connected_accounts()
    if not config['accounts']:
        return accounts_list
    print(accounts_list)
    index = int(input('Enter the account number to delete: ')) - 1
    if 0 <= index < len(config['accounts']):
        del config['accounts'][index]
        save_config()
        return f'✅ Account deleted successfully.\n'
    else:
        return '❌ Invalid account number.\n'

# Quarantine a blacklisted account
def blacklist_account(index):
    if 0 <= index < len(config['accounts']):
        config['accounts'][index]['blacklisted'] = True
        config['accounts'][index]['blacklist_time'] = time.time()
        save_config()
        return f'✅ Account quarantined for 48 hours.\n'
    else:
        return '❌ Invalid account number.\n'

# Check blacklisted accounts to lift quarantine after 48 hours
def check_blacklisted_accounts():
    for account in config['accounts']:
        if account['blacklisted'] and account['blacklist_time'] and time.time() - account['blacklist_time'] > 48 * 3600:
            account['blacklisted'] = False
            account['blacklist_time'] = None
    save_config()

# Select an account and check for restrictions
def select_account_and_check_restrictions():
    accounts_list = list_connected_accounts()
    if not config['accounts']:
        return accounts_list
    print(accounts_list)
    index = int(input('Enter the account number to check: ')) - 1
    if 0 <= index < len(config['accounts']):
        account = config['accounts'][index]
        if account['blacklisted']:
            return f"🔴 Account {account['phone']} is currently quarantined.\n"
        client = get_client(account)
        try:
            client.get_me()
            return f"🟢 Account {account['phone']} is active and without restrictions.\n"
        except Exception as e:
            restriction_details = get_restriction_details(e)
            return f"🔴 Account {account['phone']} has restrictions: {restriction_details}\n"
    else:
        return '❌ Invalid account number.\n'

# Check all accounts and ask to quarantine
def check_all_accounts_restrictions():
    results = []
    for idx, account in enumerate(config['accounts']):
        if account['blacklisted']:
            results.append((idx, f"🔴 Account {account['phone']} is currently quarantined.\n"))
            continue
        client = get_client(account)
        try:
            client.get_me()
            results.append((idx, f"🟢 Account {account['phone']} is active and without restrictions.\n"))
        except Exception as e:
            restriction_details = get_restriction_details(e)
            results.append((idx, f"🔴 Account {account['phone']} has restrictions: {restriction_details}\n"))

    for idx, result in results:
        print(result)

    quarantine_choice = input("Do you want to quarantine accounts with restrictions for 48 hours? (y/n): ").lower()
    if quarantine_choice == 'y':
        for idx, result in results:
            if "restrictions" in result:
                print(blacklist_account(idx))

# Get restriction details
def get_restriction_details(exception):
    if "disconnected" in str(exception):
        return "The account is disconnected. Please check the account connection."
    elif "flood" in str(exception).lower():
        return "The account is temporarily restricted due to too many requests. Try again later."
    elif "privacy" in str(exception).lower():
        return "The account's privacy settings prevent this action."
    else:
        return str(exception)

# Check group restrictions before adding users
def check_group_restrictions(client, group):
    try:
        if not client.is_connected():
            client.connect()
        full_group = client(GetFullChannelRequest(group))
        if full_group.full_chat.restrictions:
            return "🔴 The group has restrictions that may prevent adding members.\n"
        return "🟢 The group is unrestricted for adding members.\n"
    except Exception as e:
        return f"❌ Error checking group restrictions: {e}\n"

# Add a proxy
def add_proxy():
    proxy = input('Enter the proxy (format: ip:port[:username:password]): ')
    config['proxies'].append(proxy)
    save_config()
    return f'✅ Proxy added successfully.\n'

# Test a proxy
def test_proxy():
    proxy = input('Enter the proxy to test (format: ip:port[:username:password]): ')
    try:
        proxy_parts = proxy.split(':')
        if len(proxy_parts) == 2:
            ip, port = proxy_parts
            TelegramClient('proxy_test', None, None, proxy=(ip, int(port))).connect()
        elif len(proxy_parts) == 4:
            ip, port, username, password = proxy_parts
            TelegramClient('proxy_test', None, None, proxy=(ip, int(port), True, username, password)).connect()
        return f"🟢 Proxy {proxy} is working correctly.\n"
    except Exception as e:
        return f"🔴 Proxy {proxy} is not working: {e}\n"

# Delete a proxy
def delete_proxy():
    proxies_list = list_proxies()
    if not config['proxies']:
        return proxies_list
    print(proxies_list)
    index = int(input('Enter the proxy number to delete: ')) - 1
    if 0 <= index < len(config['proxies']):
        del config['proxies'][index]
        save_config()
        return f'✅ Proxy deleted successfully.\n'
    else:
        return '❌ Invalid proxy number.\n'

# List proxies
def list_proxies():
    if not config['proxies']:
        return "🌐 0 connected proxies.\n"
    else:
        response = ""
        for idx, proxy in enumerate(config['proxies']):
            response += f"{idx + 1}. {proxy}\n"
        return response

# Connect to the selected account
def get_client(account):
    client = TelegramClient(account['phone'], account['api_id'], account['api_hash'])
    proxy = random.choice(config['proxies']) if config['proxies'] else None
    if proxy:
        proxy_parts = proxy.split(':')
        if len(proxy_parts) == 2:
            ip, port = proxy_parts
            client.start(proxy=(ip, int(port)))
        elif len(proxy_parts) == 4:
            ip, port, username, password = proxy_parts
            client.start(proxy=(ip, int(port), True, username, password))
    else:
        client.start()
    return client

# Reset database connection
def reset_database_connection(client):
    try:
        client.disconnect()
        client.connect()
    except Exception as e:
        print(f"⚠️ Error resetting database connection: {e}")

# Check if the user is recently online
def is_user_online(status):
    return isinstance(status, (UserStatusOnline, UserStatusRecently))

# Scrape group members
def scrape_members(client, target_group, online_only=False):
    if not client.is_connected():
        client.connect()
    print(f'🔍 Retrieving members from group {target_group.title}...')
    try:
        all_participants = client.get_participants(target_group, aggressive=True)
        if online_only:
            all_participants = [user for user in all_participants if user.status and is_user_online(user.status)]
        with open("members.csv", "w", encoding='UTF-8') as f:
            writer = csv.writer(f, delimiter=",", lineterminator="\n")
            writer.writerow(['username', 'user_id', 'access_hash', 'name', 'group', 'group_id'])
            for user in all_participants:
                username = user.username if user.username else ""
                first_name = user.first_name if user.first_name else ""
                last_name = user.last_name if user.last_name else ""
                name = (first_name + ' ' + last_name).strip()
                writer.writerow([username, user.id, user.access_hash, name, target_group.title, target_group.id])
        return f'✅ Members saved to members.csv. Total number: {len(all_participants)}.\n'
    except Exception as e:
        return f"❌ Error retrieving members: {e}\n"

# Add members to a group
def add_members(client, target_group, input_file='members.csv', num_members=None, mode="normal"):
    if not client.is_connected():
        client.connect()
    print(f'➕ Adding members to group {target_group.title}...')
    users = []
    with open(input_file, encoding='UTF-8') as f:
        rows = csv.reader(f, delimiter=",", lineterminator="\n")
        next(rows, None)
        for row in rows:
            user = {'username': row[0], 'id': int(row[1]), 'access_hash': int(row[2]), 'name': row[3], 'group': row[4], 'group_id': row[5]}
            users.append(user)

    if num_members is None or num_members == '':
        num_members = len(users)
    else:
        num_members = int(num_members)

    target_group_entity = InputPeerChannel(target_group.id, target_group.access_hash)

    for user in users[:num_members]:
        try:
            print(f"➕ Adding {user['id']} ({user['username']})")
            user_to_add = InputPeerUser(user['id'], user['access_hash'])
            client(InviteToChannelRequest(target_group_entity, [user_to_add]))
            print(f'✅ {user["name"]} added successfully\n')
            if mode == "turbo":
                time.sleep(random.uniform(3, 15))
            else:
                time.sleep(random.uniform(15, 35))
        except PeerFloodError:
            return "🚫 Flood error. Script stopped. Try again after some time (24h).\n"
        except UserPrivacyRestrictedError:
            print(f"🔒 {user['username']}'s privacy settings prevent this addition.\n")
        except FloodWaitError as e:
            print(f"⏳ Wait required: {e.seconds} seconds.")
            time.sleep(e.seconds)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}\n")
            continue
    return "✅ Adding members completed.\n"

# Choose a group from active groups we can scrape
def choose_group_from_active(client):
    if not client.is_connected():
        client.connect()
    chats = []
    last_date = None
    chunk_size = 200
    result = client(GetDialogsRequest(offset_date=last_date, offset_id=0, offset_peer=InputPeerEmpty(), limit=chunk_size, hash=0))
    chats.extend(result.chats)
    groups = [chat for chat in chats if hasattr(chat, 'megagroup') and chat.megagroup and (chat.creator or (chat.admin_rights and chat.admin_rights.add_admins))]

    if not groups:
        return None, "❌ No groups available for scraping.\n"

    print('Choose a group:')
    for i, group in enumerate(groups):
        print(f"{i} - {group.title}")

    g_index = int(input("📋 Enter a number: "))
    return groups[g_index], ""

# Get a group by its name, ID or link
def get_group_by_name(client, group_identifier):
    for _ in range(3):  # Retry logic to handle database lock
        try:
            if not client.is_connected():
                client.connect()
            if group_identifier.startswith("https://t.me/"):
                username = group_identifier.split('/')[-1]
                full_group = client(ResolveUsernameRequest(username))
            elif group_identifier.isdigit():
                full_group = client(GetFullChannelRequest(int(group_identifier)))
            else:
                full_group = client(GetFullChannelRequest(group_identifier))
            return full_group.chats[0], ""
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print("🔒 Database is locked, retrying...")
                reset_database_connection(client)  # Reset the database connection
                time.sleep(2)  # Wait before retrying
            else:
                return None, f"❌ Error retrieving group: {e}\n"
        except Exception as e:
            return None, f"❌ Error retrieving group: {e}\n"
    return None, "❌ Database is locked after multiple attempts.\n"

# Delete saved users
def delete_saved_users():
    try:
        with open("members.csv", "w", encoding='UTF-8') as f:
            f.truncate()
        return '🗑️ Saved users deleted successfully.\n'
    except Exception as e:
        return f"❌ Error deleting saved users: {e}\n"

# Display saved users
def display_saved_users():
    try:
        if not os.path.exists("members.csv"):
            return "❌ No saved users.\n"
        with open("members.csv", encoding='UTF-8') as f:
            rows = csv.reader(f, delimiter=",", lineterminator="\n")
            next(rows, None)
            users = [row for row in rows]
            if not users:
                return "📋 No saved users.\n"
            response = ""
            for row in users:
                response += f"👤 {row[3]} (Username: {row[0]}, ID: {row[1]})\n"
            response += f"📊 Total number of scraped users: {len(users)}\n"
            return response
    except Exception as e:
        return f"❌ Error displaying saved users: {e}\n"

# Filter and remove inactive or fake accounts
def filter_and_remove_inactive_or_fake():
    try:
        with open("members.csv", encoding='UTF-8') as f:
            rows = csv.reader(f, delimiter=",", lineterminator="\n")
            next(rows, None)
            active_users = []
            for row in rows:
                if row[0] and int(row[1]) > 0:
                    active_users.append(row)

        with open("members.csv", "w", encoding='UTF-8') as f:
            writer = csv.writer(f, delimiter=",", lineterminator="\n")
            writer.writerow(['username', 'user_id', 'access_hash', 'name', 'group', 'group_id'])
            for user in active_users:
                writer.writerow(user)

        return f"✅ Total number of active users after filtering: {len(active_users)}\n"
    except Exception as e:
        return f"❌ Error filtering users: {e}\n"

# Save scraped members to a new CSV file
def save_scrapped_members_as():
    new_file_name = input("Enter the name of the new CSV file (without extension): ") + '.csv'
    if os.path.exists("members.csv"):
        with open("members.csv", encoding='UTF-8') as f:
            rows = f.readlines()
        with open(new_file_name, "w", encoding='UTF-8') as f:
            f.writelines(rows)
        return f"✅ Members saved to {new_file_name}.\n"
    else:
        return "❌ No member data to save.\n"

# Add scraped members to an existing CSV file or create a new one
def save_scrapped_members_append_or_overwrite():
    new_file_name = input("Enter the name of the CSV file (without extension) : ") + '.csv'
    if os.path.exists(new_file_name):
        choice = input("The file already exists. Enter 'a' to append, 'o' to overwrite : ").lower()
        if choice == 'a':
            if os.path.exists("members.csv"):
                with open("members.csv", encoding='UTF-8') as f:
                    new_rows = f.readlines()[1:]
                with open(new_file_name, "a", encoding='UTF-8') as f:
                    f.writelines(new_rows)
                return f"✅ Members added to {new_file_name}.\n"
            else:
                return "❌ No member data to add.\n"
        elif choice == 'o':
            return save_scrapped_members_as()
        else:
            return "❌ Invalid choice.\n"
    else:
        return save_scrapped_members_as()

# Display, list, and delete backup CSV files
def manage_backup_files():
    backup_files = [f for f in os.listdir() if f.endswith('.csv') and f != 'members.csv']
    if not backup_files:
        return "❌ No backup files found.\n"

    print("Available backup files:")
    for i, file in enumerate(backup_files):
        print(f"{i + 1}. {file}")

    choice = input("Enter 'v' to view the contents, 's' to delete a file, or 'q' to quit: ").lower()
    if choice == 'v':
        index = int(input("Enter the number of the file to display: ")) - 1
        if 0 <= index < len(backup_files):
            with open(backup_files[index], encoding='UTF-8') as f:
                rows = csv.reader(f, delimiter=",", lineterminator="\n")
                next(rows, None)
                users = [row for row in rows]
                response = ""
                for row in users:
                    response += f"👤 {row[3]} (Username: {row[0]}, ID: {row[1]})\n"
                response += f"📊 Total number of users: {len(users)}\n"
                return response
        else:
            return "❌ Invalid file number.\n"
    elif choice == 's':
        index = int(input("Enter the number of the file to delete: ")) - 1
        if 0 <= index < len(backup_files):
            os.remove(backup_files[index])
            return f"🗑️ File {backup_files[index]} deleted successfully.\n"
        else:
            return "❌ Invalid file number.\n"
    elif choice == 'q':
        return
    else:
        return "❌ Invalid choice.\n"

# Clone messages from a competitor group
def clone_group_messages(client, source_group):
    if not client.is_connected():
        client.connect()
    print(f'🔍 Cloning messages from group {source_group.title}...')
    try:
        messages = []
        offset_id = 0
        limit = 100
        while True:
            history = client(GetHistoryRequest(
                peer=source_group,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))
            if not history.messages:
                break
            messages.extend(history.messages)
            offset_id = min(msg.id for msg in history.messages)

        with open("cloned_messages.csv", "w", encoding='UTF-8') as f:
            writer = csv.writer(f, delimiter=",", lineterminator="\n")
            writer.writerow(['message_id', 'from_id', 'message', 'date'])
            for message in messages:
                writer.writerow([message.id, message.from_id, message.message, message.date])
        return f'✅ Messages cloned saved to cloned_messages.csv. Total number: {len(messages)}.\n'
    except Exception as e:
        return f"❌ Error cloning messages: {e}\n"

# Send cloned messages to a group
def send_cloned_messages(client, target_group, input_file='cloned_messages.csv', mode="normal"):
    if not client.is_connected():
        client.connect()
    print(f'🚀 Sending cloned messages to group {target_group.title}...')
    try:
        with open(input_file, encoding='UTF-8') as f:
            rows = csv.reader(f, delimiter=",", lineterminator="\n")
            next(rows, None)
            for row in rows:
                message_id, from_id, message, date = row
                client.send_message(target_group, message)
                if mode == "rapid":
                    time.sleep(random.uniform(5, 9))
                else:
                    time.sleep(random.uniform(15, 25))
        return "✅ Sending messages completed.\n"
    except Exception as e:
        return f"❌ Error sending messages: {e}\n"

# Display cloned messages
def display_cloned_messages():
    try:
        if not os.path.exists("cloned_messages.csv"):
            return "❌ No cloned messages.\n"
        with open("cloned_messages.csv", encoding='UTF-8') as f:
            rows = csv.reader(f, delimiter=",", lineterminator="\n")
            next(rows, None)
            messages = [row for row in rows]
            if not messages:
                return "📋 No cloned messages.\n"
            response = ""
            for row in messages:
                response += f"💬 {row[2]} (From ID: {row[1]}, Date: {row[3]})\n"
            response += f"📊 Total number of cloned messages: {len(messages)}.\n"
            return response
    except Exception as e:
        return f"❌ Error displaying cloned messages: {e}\n"

# Edit cloned messages
def edit_cloned_messages():
    try:
        if not os.path.exists("cloned_messages.csv"):
            return "❌ No cloned messages to edit.\n"
        with open("cloned_messages.csv", encoding='UTF-8') as f:
            rows = list(csv.reader(f, delimiter=",", lineterminator="\n"))
            header = rows[0]
            messages = rows[1:]
            if not messages:
                return "📋 No cloned messages to edit.\n"

        print("Available cloned messages for editing:")
        for i, row in enumerate(messages):
            print(f"{i + 1}. 💬 {row[2]} (From ID: {row[1]}, Date: {row[3]})")

        index = int(input("Enter the message number to edit: ")) - 1
        if 0 <= index < len(messages):
            new_message = input("Enter the new message content: ")
            messages[index][2] = new_message
            with open("cloned_messages.csv", "w", encoding='UTF-8') as f:
                writer = csv.writer(f, delimiter=",", lineterminator="\n")
                writer.writerow(header)
                writer.writerows(messages)
            return "✅ Message edited successfully.\n"
        else:
            return "❌ Invalid message number.\n"
    except Exception as e:
        return f"❌ Error editing cloned messages: {e}\n"

# Delete cloned messages
def delete_cloned_messages():
    try:
        if os.path.exists("cloned_messages.csv"):
            os.remove("cloned_messages.csv")
            return "🗑️ Cloned messages deleted successfully.\n"
        else:
            return "❌ No cloned messages to delete.\n"
    except Exception as e:
        return f"❌ Error deleting cloned messages: {e}\n"

# Clear cache
def clear_cache():
    try:
        if os.path.exists("cache"):
            for root, dirs, files in os.walk("cache"):
                for file in files:
                    os.remove(os.path.join(root, file))
            return "🗑️ Cache cleared successfully.\n"
        else:
            return "❌ No cache to clear.\n"
    except Exception as e:
        return f"❌ Error clearing cache: {e}\n"

# Loading animation
def loading_animation(action, delay=0.1):
    while action['running']:
        for frame in r"-\|/-\|/":
            print("\rLoading " + frame, end="")
            time.sleep(delay)
    print("\rDone!           ")

# Main menu
def main():
    check_blacklisted_accounts()
    while True:
        print("\n" + Fore.GREEN + "====== Main Menu ======" + Style.RESET_ALL)

        print(Fore.BLUE + "\n--- Account Management ---" + Style.RESET_ALL)
        print("8 - 🔌 Connect a new account")
        print("9 - 📋 List connected accounts")
        print("10 - 🗑️ Delete a connected account")
        print("11 - ⏸️ Quarantine a blacklisted account (48h)")
        print("17 - 🔍 Select an account and check for restrictions")
        print("19 - 🔍 Check restrictions on all accounts")

        print(Fore.CYAN + "\n--- Proxy Management ---" + Style.RESET_ALL)
        print("12 - 🛡️ Add a proxy")
        print("13 - ❌ Delete a proxy")
        print("14 - 🌐 List proxies")
        print("18 - 🌐 Test a proxy")

        print(Fore.YELLOW + "\n--- User Management ---" + Style.RESET_ALL)
        print("1 - 🕵️ Scrape users")
        print("2 - ➕ Add users to a group")
        print("3 - 🗑️ Delete saved users")
        print("4 - 👥 Display saved users")
        print("5 - 🚮 Filter and remove inactive/fake users")

        print(Fore.MAGENTA + "\n--- CSV File Management ---" + Style.RESET_ALL)
        print("6 - 💾 Save scraped members to a new CSV file")
        print("7 - 📂 Manage backup CSV files")
        print("16 - 💾 Save scraped members by appending or overwriting")

        print(Fore.LIGHTGREEN_EX + "\n--- Message Management ---" + Style.RESET_ALL)
        print("20 - 📋 Clone messages from a competitor group")
        print("21 - 🚀 Send cloned messages to a group")
        print("22 - 👁️ Display cloned messages")
        print("23 - ✏️ Edit cloned messages")
        print("24 - 🗑️ Delete cloned messages")

        print(Fore.RED + "\n--- Other ---" + Style.RESET_ALL)
        print("25 - 🗑️ Clear cache")

        print(Fore.RED + "\n15 - 🚪 Quit" + Style.RESET_ALL)

        choice = input("\nEnter your choice: ")

        result = ""
        if choice == '1':
            if not config['accounts']:
                result = "❌ No connected accounts. Please connect an account first.\n"
            else:
                print("Options to scrape users:")
                print("1 - Via active groups on the connected account")
                print("2 - Enter the name, ID or link of the group to scrape")

                sub_choice = input("Enter your choice: ")

                if sub_choice == '1':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ The selected account is blacklisted. Please choose another.\n"
                    else:
                        client = get_client(account)
                        source_group, error = choose_group_from_active(client)
                        if error:
                            result = error
                        else:
                            print("Options for users to scrape:")
                            print("1 - All users")
                            print("2 - Only online users")

                            online_choice = input("Enter your choice: ")
                            online_only = True if online_choice == '2' else False

                            result = scrape_members(client, source_group, online_only=online_only)

                elif sub_choice == '2':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ The selected account is blacklisted. Please choose another.\n"
                    else:
                        client = get_client(account)
                        group_identifier = input("Enter the name, ID or link of the group to scrape: ")
                        source_group, error = get_group_by_name(client, group_identifier)
                        if error:
                            result = error
                        else:
                            print("Options for users to scrape:")
                            print("1 - All users")
                            print("2 - Only online users")

                            online_choice = input("Enter your choice: ")
                            online_only = True if online_choice == '2' else False

                            result = scrape_members(client, source_group, online_only=online_only)
                else:
                    result = "Invalid choice\n"

        elif choice == '2':
            if not config['accounts']:
                result = "❌ No connected accounts. Please connect an account first.\n"
            else:
                print("Options for the target group:")
                print("1 - Add members to an active group on the connected account")
                print("2 - Enter the name, ID or link of the target group")

                sub_choice = input("Enter your choice: ")

                if sub_choice == '1':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ The selected account is blacklisted. Please choose another.\n"
                    else:
                        client = get_client(account)
                        target_group, error = choose_group_from_active(client)
                        if error:
                            result = error
                        else:
                            result = check_group_restrictions(client, target_group)
                            if "🔴" in result:
                                print(result)
                            else:
                                input_file = input("Enter the name of the CSV file to use (press Enter to use 'members.csv') : ")
                                if not input_file:
                                    input_file = 'members.csv'
                                if not os.path.exists(input_file):
                                    result = f"❌ The file {input_file} does not exist.\n"
                                else:
                                    with open(input_file, encoding='UTF-8') as f:
                                        rows = list(csv.reader(f, delimiter=",", lineterminator="\n"))
                                        num_available_members = len(rows) - 1
                                    num_members_to_add = input(f"Enter the number of members to add (Available: {num_available_members}, press Enter to add all) : ")
                                    mode = input("Enter 'normal' for normal mode (15-35s) or 'turbo' for turbo mode (3-15s) : ").lower()
                                    result = add_members(client, target_group, input_file=input_file, num_members=num_members_to_add, mode=mode)

                elif sub_choice == '2':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ The selected account is blacklisted. Please choose another.\n"
                    else:
                        client = get_client(account)
                        group_identifier = input("Enter the name, ID or link of the target group: ")
                        target_group, error = get_group_by_name(client, group_identifier)
                        if error:
                            result = error
                        else:
                            result = check_group_restrictions(client, target_group)
                            if "🔴" in result:
                                print(result)
                            else:
                                input_file = input("Enter the name of the CSV file to use (press Enter to use 'members.csv') : ")
                                if not input_file:
                                    input_file = 'members.csv'
                                if not os.path.exists(input_file):
                                    result = f"❌ The file {input_file} does not exist.\n"
                                else:
                                    with open(input_file, encoding='UTF-8') as f:
                                        rows = list(csv.reader(f, delimiter=",", lineterminator="\n"))
                                        num_available_members = len(rows) - 1
                                    num_members_to_add = input(f"Enter the number of members to add (Available: {num_available_members}, press Enter to add all) : ")
                                    mode = input("Enter 'normal' for normal mode (15-35s) or 'turbo' for turbo mode (3-15s) : ").lower()
                                    result = add_members(client, target_group, input_file=input_file, num_members=num_members_to_add, mode=mode)
                else:
                    result = "Invalid choice\n"

        elif choice == '3':
            result = delete_saved_users()

        elif choice == '4':
            result = display_saved_users()

        elif choice == '5':
            result = filter_and_remove_inactive_or_fake()

        elif choice == '6':
            result = save_scrapped_members_as()

        elif choice == '7':
            result = manage_backup_files()

        elif choice == '8':
            result = connect_new_account()

        elif choice == '9':
            result = list_connected_accounts()

        elif choice == '10':
            result = delete_connected_account()

        elif choice == '11':
            accounts_list = list_connected_accounts()
            if not config['accounts']:
                result = accounts_list
            else:
                print(accounts_list)
                index = int(input('Enter the account number to quarantine (48h): ')) - 1
                result = blacklist_account(index)

        elif choice == '12':
            result = add_proxy()

        elif choice == '13':
            result = delete_proxy()

        elif choice == '14':
            result = list_proxies()

        elif choice == '15':
            print("🚪 Quit")
            break

        elif choice == '16':
            result = save_scrapped_members_append_or_overwrite()

        elif choice == '17':
            result = select_account_and_check_restrictions()

        elif choice == '18':
            result = test_proxy()

        elif choice == '19':
            check_all_accounts_restrictions()
            result = ""

        elif choice == '20':
            if not config['accounts']:
                result = "❌ No connected accounts. Please connect an account first.\n"
            else:
                account = random.choice(config['accounts'])
                if account['blacklisted']:
                    result = "❌ The selected account is blacklisted. Please choose another.\n"
                else:
                    client = get_client(account)
                    group_identifier = input("Enter the name, ID or link of the competitor group: ")
                    source_group, error = get_group_by_name(client, group_identifier)
                    if error:
                        result = error
                    else:
                        result = clone_group_messages(client, source_group)

        elif choice == '21':
            if not config['accounts']:
                result = "❌ No connected accounts. Please connect an account first.\n"
            else:
                account = random.choice(config['accounts'])
                if account['blacklisted']:
                    result = "❌ The selected account is blacklisted. Please choose another.\n"
                else:
                    client = get_client(account)
                    group_identifier = input("Enter the name, ID or link of the target group: ")
                    target_group, error = get_group_by_name(client, group_identifier)
                    if error:
                        result = error
                    else:
                        input_file = input("Enter the name of the CSV file to use (press Enter to use 'cloned_messages.csv') : ")
                        if not input_file:
                            input_file = 'cloned_messages.csv'
                        mode = input("Enter 'normal' for normal mode (15-25s) or 'rapid' for rapid mode (5-9s): ").lower()
                        result = send_cloned_messages(client, target_group, input_file=input_file, mode=mode)

        elif choice == '22':
            result = display_cloned_messages()

        elif choice == '23':
            result = edit_cloned_messages()

        elif choice == '24':
            result = delete_cloned_messages()

        elif choice == '25':
            result = clear_cache()

        else:
            result = "Invalid choice\n"

        if result:
            print(result)

if __name__ == "__main__":
    main()

