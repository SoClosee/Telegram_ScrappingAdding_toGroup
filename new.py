import os
import json
import csv
import time
import random
import threading
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest, GetHistoryRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser, UserStatusRecently, UserStatusOnline, UserStatusOffline, PeerChannel
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError
from telethon.tl.functions.channels import InviteToChannelRequest, GetFullChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from colorama import Fore, Style
import sqlite3
import sys

# Charger la configuration
config_file = 'config.json'
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
else:
    config = {
        "accounts": [],
        "proxies": []
    }

# Enregistrer la configuration
def save_config():
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

# Animation de chargement
def loading_animation(message):
    stop_loading = threading.Event()

    def animate():
        for c in itertools.cycle(['|', '/', '-', '\\']):
            if stop_loading.is_set():
                break
            sys.stdout.write(f'\r{message} {c}')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r')

    t = threading.Thread(target=animate)
    t.start()

    return stop_loading

# Connecter un nouveau compte
def connect_new_account():
    method = input("Entrez '1' pour utiliser l'API ID et le hash, '2' pour entrer le numéro de téléphone: ")
    if method == '1':
        api_id = input('Entrez l\'API ID: ')
        api_hash = input('Entrez l\'API Hash: ')
        phone = input('Entrez le numéro de téléphone: ')
        client = TelegramClient(phone, api_id, api_hash)
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            client.sign_in(phone, input('📱 Entrez le code: '))
        config['accounts'].append({
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "blacklisted": False,
            "blacklist_time": None
        })
        save_config()
        return f'✅ Compte {phone} connecté avec succès.\n'

    elif method == '2':
        phone = input('Entrez le numéro de téléphone: ')
        api_id = input('Entrez l\'API ID: ')
        api_hash = input('Entrez l\'API Hash: ')
        client = TelegramClient(phone, api_id, api_hash)
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input('📱 Entrez le code: ')
            client.sign_in(phone, code)
        config['accounts'].append({
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "blacklisted": False,
            "blacklist_time": None
        })
        save_config()
        return f'✅ Compte {phone} connecté avec succès.\n'
    else:
        return "❌ Choix invalide"

# Lister les comptes connectés
def list_connected_accounts():
    if not config['accounts']:
        return "📋 0 compte connecté.\n"
    else:
        response = ""
        for idx, account in enumerate(config['accounts']):
            status = "🔴 Blacklisted" if account['blacklisted'] else "🟢 Active"
            response += f"{idx + 1}. {account['phone']} - {status}\n"
        return response

# Supprimer un compte connecté
def delete_connected_account():
    accounts_list = list_connected_accounts()
    if not config['accounts']:
        return accounts_list
    print(accounts_list)
    index = int(input('Entrez le numéro du compte à supprimer: ')) - 1
    if 0 <= index < len(config['accounts']):
        del config['accounts'][index]
        save_config()
        return f'✅ Compte supprimé avec succès.\n'
    else:
        return '❌ Numéro de compte invalide.\n'

# Mettre en quarantaine un compte blacklisté
def blacklist_account(index):
    if 0 <= index < len(config['accounts']):
        config['accounts'][index]['blacklisted'] = True
        config['accounts'][index]['blacklist_time'] = time.time()
        save_config()
        return f'✅ Compte mis en quarantaine pour 48 heures.\n'
    else:
        return '❌ Numéro de compte invalide.\n'

# Vérifier les comptes blacklistés pour lever la quarantaine après 48h
def check_blacklisted_accounts():
    for account in config['accounts']:
        if account['blacklisted'] and account['blacklist_time'] and time.time() - account['blacklist_time'] > 48 * 3600:
            account['blacklisted'] = False
            account['blacklist_time'] = None
    save_config()

# Sélectionner un compte et vérifier les restrictions
def select_account_and_check_restrictions():
    accounts_list = list_connected_accounts()
    if not config['accounts']:
        return accounts_list
    print(accounts_list)
    index = int(input('Entrez le numéro du compte à vérifier: ')) - 1
    if 0 <= index < len(config['accounts']):
        account = config['accounts'][index]
        if account['blacklisted']:
            return f"🔴 Le compte {account['phone']} est actuellement en quarantaine.\n"
        client = get_client(account)
        try:
            client.get_me()
            return f"🟢 Le compte {account['phone']} est actif et sans restrictions.\n"
        except Exception as e:
            restriction_details = get_restriction_details(e)
            return f"🔴 Le compte {account['phone']} a des restrictions: {restriction_details}\n"
    else:
        return '❌ Numéro de compte invalide.\n'

# Vérifier tous les comptes et demander de les mettre en quarantaine
def check_all_accounts_restrictions():
    results = []
    for idx, account in enumerate(config['accounts']):
        if account['blacklisted']:
            results.append((idx, f"🔴 Le compte {account['phone']} est actuellement en quarantaine.\n"))
            continue
        client = get_client(account)
        try:
            client.get_me()
            results.append((idx, f"🟢 Le compte {account['phone']} est actif et sans restrictions.\n"))
        except Exception as e:
            restriction_details = get_restriction_details(e)
            results.append((idx, f"🔴 Le compte {account['phone']} a des restrictions: {restriction_details}\n"))

    for idx, result in results:
        print(result)

    quarantine_choice = input("Voulez-vous mettre les comptes avec des restrictions en quarantaine pendant 48 heures ? (o/n): ").lower()
    if quarantine_choice == 'o':
        for idx, result in results:
            if "restrictions" in result:
                print(blacklist_account(idx))

# Obtenir les détails sur la restriction
def get_restriction_details(exception):
    if "disconnected" in str(exception):
        return "Le compte est déconnecté. Veuillez vérifier la connexion du compte."
    elif "flood" in str(exception).lower():
        return "Le compte est temporairement restreint en raison d'un nombre excessif de requêtes. Essayez à nouveau plus tard."
    elif "privacy" in str(exception).lower():
        return "Les paramètres de confidentialité du compte empêchent cette action."
    else:
        return str(exception)

# Vérifier les restrictions sur le groupe cible avant d'ajouter des utilisateurs
def check_group_restrictions(client, group):
    try:
        if not client.is_connected():
            client.connect()
        full_group = client(GetFullChannelRequest(group))
        if full_group.full_chat.restrictions:
            return "🔴 Le groupe a des restrictions qui peuvent empêcher l'ajout de membres.\n"
        return "🟢 Le groupe est sans restrictions pour l'ajout de membres.\n"
    except Exception as e:
        return f"❌ Erreur lors de la vérification des restrictions du groupe: {e}\n"

# Ajouter un proxy
def add_proxy():
    proxy = input('Entrez le proxy (format: ip:port[:username:password]): ')
    config['proxies'].append(proxy)
    save_config()
    return f'✅ Proxy ajouté avec succès.\n'

# Tester un proxy
def test_proxy():
    proxy = input('Entrez le proxy à tester (format: ip:port[:username:password]): ')
    try:
        proxy_parts = proxy.split(':')
        if len(proxy_parts) == 2:
            ip, port = proxy_parts
            TelegramClient('proxy_test', None, None, proxy=(ip, int(port))).connect()
        elif len(proxy_parts) == 4:
            ip, port, username, password = proxy_parts
            TelegramClient('proxy_test', None, None, proxy=(ip, int(port), True, username, password)).connect()
        return f"🟢 Proxy {proxy} fonctionne correctement.\n"
    except Exception as e:
        return f"🔴 Proxy {proxy} ne fonctionne pas: {e}\n"

# Supprimer un proxy
def delete_proxy():
    proxies_list = list_proxies()
    if not config['proxies']:
        return proxies_list
    print(proxies_list)
    index = int(input('Entrez le numéro du proxy à supprimer: ')) - 1
    if 0 <= index < len(config['proxies']):
        del config['proxies'][index]
        save_config()
        return f'✅ Proxy supprimé avec succès.\n'
    else:
        return '❌ Numéro de proxy invalide.\n'

# Lister les proxys
def list_proxies():
    if not config['proxies']:
        return "🌐 0 proxy connecté.\n"
    else:
        response = ""
        for idx, proxy in enumerate(config['proxies']):
            response += f"{idx + 1}. {proxy}\n"
        return response

# Connecter au compte sélectionné
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

# Réinitialiser la connexion à la base de données
def reset_database_connection(client):
    try:
        client.disconnect()
        client.connect()
    except Exception as e:
        print(f"⚠️ Erreur lors de la réinitialisation de la connexion à la base de données: {e}")

# Vérifier si l'utilisateur est récemment en ligne
def is_user_online(status):
    return isinstance(status, (UserStatusOnline, UserStatusRecently))

# Scraper les membres d'un groupe
def scrape_members(client, target_group, online_only=False):
    stop_loading = loading_animation("🔍 Récupération des membres du groupe...")
    try:
        if not client.is_connected():
            client.connect()
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
        return f'✅ Membres enregistrés dans members.csv. Nombre total: {len(all_participants)}.\n'
    except Exception as e:
        return f"❌ Erreur lors de la récupération des membres: {e}\n"
    finally:
        stop_loading.set()

# Ajouter des membres à un groupe
def add_members(client, target_group, input_file='members.csv', num_members=None, mode="normal"):
    if not client.is_connected():
        client.connect()
    print(f'➕ Ajout de membres au groupe {target_group.title}...')
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
            print(f"➕ Ajout de {user['id']} ({user['username']})")
            user_to_add = InputPeerUser(user['id'], user['access_hash'])
            client(InviteToChannelRequest(target_group_entity, [user_to_add]))
            print(f'✅ {user["name"]} ajouté avec succès\n')
            if mode == "turbo":
                time.sleep(random.uniform(3, 15))
            else:
                time.sleep(random.uniform(15, 35))
        except PeerFloodError:
            return "🚫 Erreur d'inondation. Script arrêté. Réessayez après un certain temps (24h).\n"
        except UserPrivacyRestrictedError:
            print(f"🔒 Les paramètres de confidentialité de {user['username']} ne permettent pas cet ajout.\n")
        except FloodWaitError as e:
            print(f"⏳ Attente requise : {e.seconds} secondes.")
            time.sleep(e.seconds)
        except Exception as e:
            print(f"⚠️ Erreur inattendue: {e}\n")
            continue
    return "✅ Ajout des membres terminé.\n"

# Choisir un groupe à partir des groupes actifs où nous pouvons scrapper
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
        return None, "❌ Aucun groupe disponible pour le scrapping.\n"

    print('Choisissez un groupe:')
    for i, group in enumerate(groups):
        print(f"{i} - {group.title}")

    g_index = int(input("📋 Entrez un numéro: "))
    return groups[g_index], ""

# Obtenir un groupe par son nom, ID ou lien
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
                print("🔒 La base de données est verrouillée, nouvelle tentative...")
                reset_database_connection(client)  # Reset the database connection
                time.sleep(2)  # Wait before retrying
            else:
                return None, f"❌ Erreur lors de la récupération du groupe: {e}\n"
        except Exception as e:
            return None, f"❌ Erreur lors de la récupération du groupe: {e}\n"
    return None, "❌ La base de données est verrouillée après plusieurs tentatives.\n"

# Supprimer les utilisateurs enregistrés
def delete_saved_users():
    try:
        with open("members.csv", "w", encoding='UTF-8') as f:
            f.truncate()
        return '🗑️ Utilisateurs enregistrés supprimés avec succès.\n'
    except Exception as e:
        return f"❌ Erreur lors de la suppression des utilisateurs enregistrés: {e}\n"

# Afficher les utilisateurs enregistrés
def display_saved_users():
    try:
        if not os.path.exists("members.csv"):
            return "❌ Aucun utilisateur enregistré.\n"
        with open("members.csv", encoding='UTF-8') as f:
            rows = csv.reader(f, delimiter=",", lineterminator="\n")
            next(rows, None)
            users = [row for row in rows]
            if not users:
                return "📋 Aucun utilisateur enregistré.\n"
            response = ""
            for row in users:
                response += f"👤 {row[3]} (Username: {row[0]}, ID: {row[1]})\n"
            response += f"📊 Nombre total d'utilisateurs scrappés: {len(users)}\n"
            return response
    except Exception as e:
        return f"❌ Erreur lors de l'affichage des utilisateurs enregistrés: {e}\n"

# Filtrer et supprimer les membres non actifs ou les faux comptes
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

        return f"✅ Nombre total d'utilisateurs actifs après filtrage: {len(active_users)}\n"
    except Exception as e:
        return f"❌ Erreur lors du filtrage des utilisateurs: {e}\n"

# Enregistrer les membres scrappés dans un nouveau fichier CSV
def save_scrapped_members_as():
    new_file_name = input("Entrez le nom du nouveau fichier CSV (sans extension): ") + '.csv'
    if os.path.exists("members.csv"):
        with open("members.csv", encoding='UTF-8') as f:
            rows = f.readlines()
        with open(new_file_name, "w", encoding='UTF-8') as f:
            f.writelines(rows)
        return f"✅ Membres enregistrés dans {new_file_name}.\n"
    else:
        return "❌ Aucune donnée de membre à enregistrer.\n"

# Ajouter les membres scrappés à un fichier CSV existant ou créer un nouveau
def save_scrapped_members_append_or_overwrite():
    new_file_name = input("Entrez le nom du fichier CSV (sans extension) : ") + '.csv'
    if os.path.exists(new_file_name):
        choice = input("Le fichier existe déjà. Entrez 'a' pour ajouter, 'o' pour écraser : ").lower()
        if choice == 'a':
            if os.path.exists("members.csv"):
                with open("members.csv", encoding='UTF-8') as f:
                    new_rows = f.readlines()[1:]
                with open(new_file_name, "a", encoding='UTF-8') as f:
                    f.writelines(new_rows)
                return f"✅ Membres ajoutés à {new_file_name}.\n"
            else:
                return "❌ Aucune donnée de membre à ajouter.\n"
        elif choice == 'o':
            return save_scrapped_members_as()
        else:
            return "❌ Choix invalide.\n"
    else:
        return save_scrapped_members_as()

# Afficher, lister et supprimer les fichiers CSV de sauvegarde
def manage_backup_files():
    backup_files = [f for f in os.listdir() if f.endswith('.csv') and f != 'members.csv']
    if not backup_files:
        return "❌ Aucun fichier de sauvegarde trouvé.\n"

    print("Fichiers de sauvegarde disponibles:")
    for i, file in enumerate(backup_files):
        print(f"{i + 1}. {file}")

    choice = input("Entrez 'v' pour voir le contenu, 's' pour supprimer un fichier, ou 'q' pour quitter: ").lower()
    if choice == 'v':
        index = int(input("Entrez le numéro du fichier à afficher: ")) - 1
        if 0 <= index < len(backup_files):
            with open(backup_files[index], encoding='UTF-8') as f:
                rows = csv.reader(f, delimiter=",", lineterminator="\n")
                next(rows, None)
                users = [row for row in rows]
                response = ""
                for row in users:
                    response += f"👤 {row[3]} (Username: {row[0]}, ID: {row[1]})\n"
                response += f"📊 Nombre total d'utilisateurs: {len(users)}\n"
                return response
        else:
            return "❌ Numéro de fichier invalide.\n"
    elif choice == 's':
        index = int(input("Entrez le numéro du fichier à supprimer: ")) - 1
        if 0 <= index < len(backup_files):
            os.remove(backup_files[index])
            return f"🗑️ Fichier {backup_files[index]} supprimé avec succès.\n"
        else:
            return "❌ Numéro de fichier invalide.\n"
    elif choice == 'q':
        return
    else:
        return "❌ Choix invalide.\n"

# Cloner les messages d'un groupe concurrent
def clone_group_messages(client, source_group):
    stop_loading = loading_animation("🔍 Clonage des messages du groupe...")
    try:
        if not client.is_connected():
            client.connect()
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
        return f'✅ Messages clonés enregistrés dans cloned_messages.csv. Nombre total: {len(messages)}.\n'
    except Exception as e:
        return f"❌ Erreur lors du clonage des messages: {e}\n"
    finally:
        stop_loading.set()

# Envoyer les messages clonés dans un groupe
def send_cloned_messages(client, target_group, input_file='cloned_messages.csv', mode="normal"):
    try:
        if not client.is_connected():
            client.connect()
        print(f'🚀 Envoi des messages clonés au groupe {target_group.title}...')
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
        return "✅ Envoi des messages terminé.\n"
    except Exception as e:
        return f"❌ Erreur lors de l'envoi des messages: {e}\n"

# Afficher les messages clonés
def display_cloned_messages():
    try:
        if not os.path.exists("cloned_messages.csv"):
            return "❌ Aucun message cloné.\n"
        with open("cloned_messages.csv", encoding='UTF-8') as f:
            rows = csv.reader(f, delimiter=",", lineterminator="\n")
            next(rows, None)
            messages = [row for row in rows]
            if not messages:
                return "📋 Aucun message cloné.\n"
            response = ""
            for row in messages:
                response += f"💬 {row[2]} (From ID: {row[1]}, Date: {row[3]})\n"
            response += f"📊 Nombre total de messages clonés: {len(messages)}.\n"
            return response
    except Exception as e:
        return f"❌ Erreur lors de l'affichage des messages clonés: {e}\n"

# Éditer les messages clonés
def edit_cloned_messages():
    try:
        if not os.path.exists("cloned_messages.csv"):
            return "❌ Aucun message cloné à éditer.\n"
        with open("cloned_messages.csv", encoding='UTF-8') as f:
            rows = list(csv.reader(f, delimiter=",", lineterminator="\n"))
            header = rows[0]
            messages = rows[1:]
            if not messages:
                return "📋 Aucun message cloné à éditer.\n"

        print("Messages clonés disponibles pour l'édition:")
        for i, row in enumerate(messages):
            print(f"{i + 1}. 💬 {row[2]} (From ID: {row[1]}, Date: {row[3]})")

        index = int(input("Entrez le numéro du message à éditer: ")) - 1
        if 0 <= index < len(messages):
            new_message = input("Entrez le nouveau contenu du message: ")
            messages[index][2] = new_message
            with open("cloned_messages.csv", "w", encoding='UTF-8') as f:
                writer = csv.writer(f, delimiter=",", lineterminator="\n")
                writer.writerow(header)
                writer.writerows(messages)
            return "✅ Message édité avec succès.\n"
        else:
            return "❌ Numéro de message invalide.\n"
    except Exception as e:
        return f"❌ Erreur lors de l'édition des messages clonés: {e}\n"

# Supprimer les messages clonés
def delete_cloned_messages():
    try:
        if os.path.exists("cloned_messages.csv"):
            os.remove("cloned_messages.csv")
            return "🗑️ Messages clonés supprimés avec succès.\n"
        else:
            return "❌ Aucun message cloné à supprimer.\n"
    except Exception as e:
        return f"❌ Erreur lors de la suppression des messages clonés: {e}\n"

# Vider le cache
def clear_cache():
    try:
        cache_files = [f for f in os.listdir() if f.endswith('.session')]
        for cache_file in cache_files:
            os.remove(cache_file)
        return "🗑️ Cache vidé avec succès.\n"
    except Exception as e:
        return f"❌ Erreur lors du vidage du cache: {e}\n"

# Menu principal
def main():
    check_blacklisted_accounts()
    while True:
        print("\n" + Fore.GREEN + "====== Menu Principal ======" + Style.RESET_ALL)
        print(Fore.GREEN + "--- Gestion des comptes ---" + Style.RESET_ALL)
        print("8 - 🔌 Connexion d'un nouveau compte")
        print("9 - 📋 Liste des comptes connectés")
        print("10 - 🗑️ Supprimer un compte connecté")
        print("11 - ⏸️ Mettre en pause (48h) un compte blacklisté")
        print("17 - 🔍 Sélectionner un compte et vérifier les restrictions")
        print("19 - 🔍 Vérifier les restrictions de tous les comptes")

        print(Fore.BLUE + "\n--- Gestion des proxys ---" + Style.RESET_ALL)
        print("12 - 🛡️ Ajouter un proxy")
        print("13 - ❌ Supprimer un proxy")
        print("14 - 🌐 Liste des proxys")
        print("18 - 🌐 Tester un proxy")

        print(Fore.YELLOW + "\n--- Gestion des utilisateurs ---" + Style.RESET_ALL)
        print("1 - 🕵️ Scrapper des users")
        print("2 - ➕ Ajouter des users dans un groupe")
        print("3 - 🗑️ Supprimer les utilisateurs enregistrés")
        print("4 - 👥 Afficher les utilisateurs scrappés")
        print("5 - 🚮 Filtrer et supprimer les utilisateurs inactifs/faux comptes")

        print(Fore.MAGENTA + "\n--- Gestion des fichiers CSV ---" + Style.RESET_ALL)
        print("6 - 💾 Sauvegarder les membres scrappés dans un nouveau fichier CSV")
        print("7 - 📂 Gérer les fichiers CSV de sauvegarde")
        print("16 - 💾 Sauvegarder les membres scrappés en ajoutant ou en écrasant")

        print(Fore.LIGHTGREEN_EX + "\n--- Gestion des messages ---" + Style.RESET_ALL)
        print("20 - 📋 Cloner les messages d'un groupe concurrent")
        print("21 - 🚀 Envoyer les messages clonés dans un groupe")
        print("22 - 👁️ Afficher les messages clonés")
        print("23 - ✏️ Éditer les messages clonés")
        print("24 - 🗑️ Supprimer les messages clonés")

        print(Fore.RED + "\n--- Autres ---" + Style.RESET_ALL)
        print("25 - 🗑️ Vider le cache")
        print("15 - 🚪 Quitter")

        choice = input("\nEntrez votre choix: ")

        result = ""
        if choice == '1':
            if not config['accounts']:
                result = "❌ Aucun compte connecté. Veuillez d'abord connecter un compte.\n"
            else:
                print("Options pour scrapper des users:")
                print("1 - Via les groupes actifs sur le compte connecté")
                print("2 - Entrer le nom, l'ID ou le lien du groupe à scrapper")

                sub_choice = input("Entrez votre choix: ")

                if sub_choice == '1':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ Le compte sélectionné est blacklisté. Veuillez en choisir un autre.\n"
                    else:
                        client = get_client(account)
                        source_group, error = choose_group_from_active(client)
                        if error:
                            result = error
                        else:
                            print("Options pour les utilisateurs à scrapper:")
                            print("1 - Tous les utilisateurs")
                            print("2 - Utilisateurs en ligne uniquement")

                            online_choice = input("Entrez votre choix: ")
                            online_only = True if online_choice == '2' else False

                            result = scrape_members(client, source_group, online_only=online_only)

                elif sub_choice == '2':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ Le compte sélectionné est blacklisté. Veuillez en choisir un autre.\n"
                    else:
                        client = get_client(account)
                        group_identifier = input("Entrez le nom, l'ID ou le lien du groupe à scrapper: ")
                        source_group, error = get_group_by_name(client, group_identifier)
                        if error:
                            result = error
                        else:
                            print("Options pour les utilisateurs à scrapper:")
                            print("1 - Tous les utilisateurs")
                            print("2 - Utilisateurs en ligne uniquement")

                            online_choice = input("Entrez votre choix: ")
                            online_only = True if online_choice == '2' else False

                            result = scrape_members(client, source_group, online_only=online_only)
                else:
                    result = "Choix invalide\n"

        elif choice == '2':
            if not config['accounts']:
                result = "❌ Aucun compte connecté. Veuillez d'abord connecter un compte.\n"
            else:
                print("Options pour le groupe cible:")
                print("1 - Ajouter des membres à un groupe actif sur le compte connecté")
                print("2 - Entrer le nom, l'ID ou le lien du groupe cible")

                sub_choice = input("Entrez votre choix: ")

                if sub_choice == '1':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ Le compte sélectionné est blacklisté. Veuillez en choisir un autre.\n"
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
                                input_file = input("Entrez le nom du fichier CSV à utiliser (appuyez sur Entrée pour utiliser 'members.csv') : ")
                                if not input_file:
                                    input_file = 'members.csv'
                                if not os.path.exists(input_file):
                                    result = f"❌ Le fichier {input_file} n'existe pas.\n"
                                else:
                                    with open(input_file, encoding='UTF-8') as f:
                                        rows = list(csv.reader(f, delimiter=",", lineterminator="\n"))
                                        num_available_members = len(rows) - 1
                                    num_members_to_add = input(f"Entrez le nombre de membres à ajouter (Disponible: {num_available_members}, appuyez sur Entrée pour tous les ajouter) : ")
                                    mode = input("Entrez 'normal' pour le mode normal (15-35s) ou 'turbo' pour le mode turbo (3-15s) : ").lower()
                                    result = add_members(client, target_group, input_file=input_file, num_members=num_members_to_add, mode=mode)

                elif sub_choice == '2':
                    account = random.choice(config['accounts'])
                    if account['blacklisted']:
                        result = "❌ Le compte sélectionné est blacklisté. Veuillez en choisir un autre.\n"
                    else:
                        client = get_client(account)
                        group_identifier = input("Entrez le nom, l'ID ou le lien du groupe cible: ")
                        target_group, error = get_group_by_name(client, group_identifier)
                        if error:
                            result = error
                        else:
                            result = check_group_restrictions(client, target_group)
                            if "🔴" in result:
                                print(result)
                            else:
                                input_file = input("Entrez le nom du fichier CSV à utiliser (appuyez sur Entrée pour utiliser 'members.csv') : ")
                                if not input_file:
                                    input_file = 'members.csv'
                                if not os.path.exists(input_file):
                                    result = f"❌ Le fichier {input_file} n'existe pas.\n"
                                else:
                                    with open(input_file, encoding='UTF-8') as f:
                                        rows = list(csv.reader(f, delimiter=",", lineterminator="\n"))
                                        num_available_members = len(rows) - 1
                                    num_members_to_add = input(f"Entrez le nombre de membres à ajouter (Disponible: {num_available_members}, appuyez sur Entrée pour tous les ajouter) : ")
                                    mode = input("Entrez 'normal' pour le mode normal (15-35s) ou 'turbo' pour le mode turbo (3-15s) : ").lower()
                                    result = add_members(client, target_group, input_file=input_file, num_members=num_members_to_add, mode=mode)
                else:
                    result = "Choix invalide\n"

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
                index = int(input('Entrez le numéro du compte à mettre en pause (48h): ')) - 1
                result = blacklist_account(index)

        elif choice == '12':
            result = add_proxy()

        elif choice == '13':
            result = delete_proxy()

        elif choice == '14':
            result = list_proxies()

        elif choice == '15':
            print("🚪 Quitter")
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
                result = "❌ Aucun compte connecté. Veuillez d'abord connecter un compte.\n"
            else:
                account = random.choice(config['accounts'])
                if account['blacklisted']:
                    result = "❌ Le compte sélectionné est blacklisté. Veuillez en choisir un autre.\n"
                else:
                    client = get_client(account)
                    group_identifier = input("Entrez le nom, l'ID ou le lien du groupe concurrent: ")
                    source_group, error = get_group_by_name(client, group_identifier)
                    if error:
                        result = error
                    else:
                        result = clone_group_messages(client, source_group)

        elif choice == '21':
            if not config['accounts']:
                result = "❌ Aucun compte connecté. Veuillez d'abord connecter un compte.\n"
            else:
                account = random.choice(config['accounts'])
                if account['blacklisted']:
                    result = "❌ Le compte sélectionné est blacklisté. Veuillez en choisir un autre.\n"
                else:
                    client = get_client(account)
                    group_identifier = input("Entrez le nom, l'ID ou le lien du groupe cible: ")
                    target_group, error = get_group_by_name(client, group_identifier)
                    if error:
                        result = error
                    else:
                        input_file = input("Entrez le nom du fichier CSV à utiliser (appuyez sur Entrée pour utiliser 'cloned_messages.csv') : ")
                        if not input_file:
                            input_file = 'cloned_messages.csv'
                        mode = input("Entrez 'normal' pour le mode normal (15-25s) ou 'rapid' pour le mode rapide (5-9s) : ").lower()
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
            result = "Choix invalide\n"

        if result:
            print(result)

if __name__ == "__main__":
    main()

