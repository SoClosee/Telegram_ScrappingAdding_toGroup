#  _______  _______  _______  _        _______  _______  _______ 
# (  ____ \(  ___  )(  ____ \( \      (  ___  )(  ____ \(  ____ \
# | (    \/| (   ) || (    \/| (      | (   ) || (    \/| (    \/
# | (_____ | |   | || |      | |      | |   | || (_____ | (__    
# (_____  )| |   | || |      | |      | |   | |(_____  )|  __)   
#       ) || |   | || |      | |      | |   | |      ) || (      
# /\____) || (___) || (____/\| (____/\| (___) |/\____) || (____/\
# \_______)(_______)(_______/(_______/(_______)\_______)(_______/


from telethon.tl.types import InputPeerChat, InputPeerUser, InputPeerChannel
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import InviteToChannelRequest
import traceback
import time
import random
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
import csv

api_id = XXXXXX
api_hash = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
phone = '+XXXXXXXXXXX'

client = TelegramClient(phone, api_id, api_hash)

client.connect()
if not client.is_user_authorized():
    client.send_code_request(phone)
    client.sign_in(phone, input('Entrer le code: '))

chats = []
last_date = None
chunk_size = 200
groups = []

result = client(GetDialogsRequest(
    offset_date=last_date,
    offset_id=0,
    offset_peer=InputPeerEmpty(),
    limit=chunk_size,
    hash=0
))
chats.extend(result.chats)

printGrp = []
for chat in chats:
    try:
        if chat.title.lower() not in printGrp:
            groups.append(chat)
            printGrp.append(chat.title.lower())
    except:
        continue

print('Choisissez un groupe dans lequel scraper les membres: ')
i = 0
for g in groups:
    print(str(i) + '- ' + g.title)
    i += 1

g_index = input("Entrez un numéro: ")
target_group = groups[int(g_index)]

print('Récupération des membres...')
all_participants = []
all_participants = client.get_participants(target_group, aggressive=True)

print('Enregistrement dans un fichier...')
with open("members.csv", "w", encoding='UTF-8') as f:
    writer = csv.writer(f, delimiter=",", lineterminator="\n")
    writer.writerow(['username', 'user id', 'access hash', 'name', 'group', 'group id'])
    for user in all_participants:
        if user.username:
            username = user.username
        else:
            username = ""
        if user.first_name:
            first_name = user.first_name
        else:
            first_name = ""
        if user.last_name:
            last_name = user.last_name
        else:
            last_name = ""
        name = (first_name + ' ' + last_name).strip()
        writer.writerow([username, user.id, user.access_hash, name, target_group.title, target_group.id])
print('Membres supprimés avec succès.')
print('----------------------------------------------')

input_file = 'members.csv'
users = []


with open("save1.txt", "r", encoding='ISO-8859-1') as txtFile:
    inputData = txtFile.read()

popTheseManyMembers = int(inputData)
print(popTheseManyMembers)


with open(input_file, encoding='UTF-8') as f:
    rows = csv.reader(f, delimiter=",", lineterminator="\n")
    next(rows, None)
    for row in rows:
        user = {}
        user['username'] = row[0]
        user['id'] = int(row[1])
        user['access_hash'] = int(row[2])
        user['name'] = row[3]
        user['group'] = row[4]
        user['group id'] = row[5]
        users.append(user)

i = 0
for i in range(popTheseManyMembers):
    users.pop(0)

chats = []
last_date = None
chunk_size = 200
groups = []

result = client(GetDialogsRequest(
    offset_date=last_date,
    offset_id=0,
    offset_peer=InputPeerEmpty(),
    limit=chunk_size,
    hash=0
))
chats.extend(result.chats)

printGrp = []
for chat in chats:
    try:
        if chat.megagroup == True:
            if chat.title.lower() not in printGrp:
                groups.append(chat)
                printGrp.append(chat.title.lower())
    except:
        continue

print('Choisissez un groupe pour ajouter des membres:')
i = 0
for group in groups:
    print(str(i) + '- ' + group.title)
    i += 1

g_index = input("Entrez un numéro: ")
target_group = groups[int(g_index)]

target_group_entity = InputPeerChannel(target_group.id, target_group.access_hash)
print('group id: ', target_group.id)
print('access_hash of group: ', target_group.access_hash)

n = 0
count = 0
for user in users:
    count += 1
    try:
        
        print("Adding {}".format(user['id']))

        print(user['id'])
        user_to_add = InputPeerUser(user['id'], user['access_hash'])

        client(InviteToChannelRequest(target_group_entity,[user_to_add]))
        time.sleep(19)
    except PeerFloodError:
        print("Erreur d'inondation à partir de telegramme. Le script s'arrête maintenant. Veuillez réessayer après un certain temps (24h).")
        n += 1
    except UserPrivacyRestrictedError:
        print("Les paramètres de confidentialité de l'utilisateur ne vous permettent pas de faire cela.")
    except:
        traceback.print_exc()
        print("Erreur inattendue")
        n += 1
        pass

    print("Le code s'arrête et enregistre les utilisateurs restants lorsque n dépasse 50")
    print("current value of n = ", n)
    if (n > 25):
        break

with open("save1.txt", "w", encoding='UTF-8') as f:
    f.write(str(count+1))