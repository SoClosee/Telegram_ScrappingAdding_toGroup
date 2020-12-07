# Bot Telegram Scrapping and Adding to a Public Group:
Le Bot permet de scrapper les informations utilisateurs dans les groupes telegram Public puis de les ajouter dans l'un de vos groupes.

## Table des matières:
* [Introduction]
* [Installation]
* [Commencer]
* [Obtenir de l'aide]

## Introduction:
Bot Telegram en Python. Permet de récupérer les membres de différents groupes et les ajouter à nos groupes dans Telegram à l'aide du forfait Téléthon.
#### Prérequis:
* Python doit être installé sur votre système
* La version 3 ou supérieure est préférée
* Les clés d'API Telegram doivent être créées à l'aide de ce lien https://my.telegram.org/auth?to=apps
#### Fonctionnalités:
* Récupérer les membres de différents groupes et les stocker dans des fichiers CSV
* Lisez les données des fichiers csv et ajoutez-les à nos groupes en utilisant les méthodes téléthon.
#### Exigences:
* Tous les packages requis sont placés dans requirements.txt
* Utilisez la commande "pip install -r -U requirements.txt" pour installer les packages requis.

## Installation:
* Installer python: 
```
$ sudo pip install python3
``` 

* Installer telethon: 
```
$ python pip install telethon
``` 

* Cloner le repositorie: 
```
$ git clone https://github.com/SoClosee/Telegram_ScrappingAdding_toGroup.git
``` 

* Aller dans le dossier:
```
$ cd Telegram_ScrappingAdding_toGroup
```

* Puis aller sur http://my.telegram.org et connectez vous
* Cliquez sur les outils de développement d'API et remplissez les champs obligatoires.
* Mettez le nom de l'application que vous voulez et sélectionnez une autre dans l'exemple de plate-forme 
* Copiez "api_id" et "api_hash" après avoir cliqué sur Créer une application. 

* Ajouter vos identifiants Api Telegram dans add1.py:
```python
api_id = XXXXXX
api_hash = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
phone = '+XXXXXXXXXXX'
```

## Commencer:
* Lancer le bot:
```
$ python add1.py
```

* Selectionner un groupe dans lequel scrapper les membres: (Entrez le numéro du groupe).
* Selectionner un groupe dans lequel ajouter les membres: (Entrez le numéro du groupe).


## Obtenir de l'aide:
Pour plus d'information n'hesite pas à nous rejoindre sur [Discord] ou sur [Telegram]!  
Découvre aussi tous nos réseaux sociaux sur lesquels nous sommes très actifs. 
<br>
[SoClose Digital Consulting Team]

[<img align="left" alt="codeSTACKr.com" width="22px" src="https://raw.githubusercontent.com/iconic/open-iconic/master/svg/globe.svg" />][website]
[<img align="left" alt="codeSTACKr | YouTube" width="22px" src="https://cdn.jsdelivr.net/npm/simple-icons@v3/icons/youtube.svg" />][youtube]
[<img align="left" alt="codeSTACKr | LinkedIn" width="22px" src="https://cdn.jsdelivr.net/npm/simple-icons@v3/icons/linkedin.svg" />][linkedin]
[<img align="left" alt="codeSTACKr | Instagram" width="22px" src="https://cdn.jsdelivr.net/npm/simple-icons@v3/icons/instagram.svg" />][instagram]

[website]: https://soclose.co
[youtube]: https://youtube.com/soclosetv
[instagram]: https://instagram.com/socloseagency
[linkedin]: https://linkedin.com/in/soclose
[introduction]: https://github.com/SoClosee/Telegram_ScrappingAdding_toGroup#introduction
[installation]: https://github.com/SoClosee/Telegram_ScrappingAdding_toGroup#installation
[Commencer]: https://github.com/SoClosee/Telegram_ScrappingAdding_toGroup#commencer
[Obtenir de l'aide]: https://github.com/SoClosee/Telegram_ScrappingAdding_toGroup#obtenir-de-laide 
[Discord]: https://discord.gg/nmFv2U3yHK
[Telegram]: https://t.me/soclosetv
[SoClose Digital Consulting Team]: https://soclose.co