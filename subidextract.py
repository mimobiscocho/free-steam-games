import requests
import re
import time
import csv
import json

# 🔐 Tes cookies Steam (obligatoire d’être connecté)
cookies = {
    'sessionid': 'SESSION ID COOKIE',
    'steamLoginSecure': 'STEAMLOGINSECURE COOIKE'
}

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://store.steampowered.com/',
    'Origin': 'https://store.steampowered.com',
    'X-Requested-With': 'XMLHttpRequest'
}

fichier_entree = "jeux_gratuits_pages_html.txt"
fichier_sortie = "subids_avec_titres.csv"

def extraire_appids(fichier):
    appids = set()
    with open(fichier, "r", encoding="utf-8") as f:
        for line in f:
            if "store.steampowered.com/app/" in line:
                try:
                    appid = line.split("/app/")[1].split("/")[0]
                    appids.add(appid)
                except IndexError:
                    continue
    return sorted(appids)

def trouver_subid_et_titre(appid):
    url = f"https://store.steampowered.com/app/{appid}/"
    response = requests.get(url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        return None, None

    match = re.search(r'AddFreeLicense\(\s*(\d+),\s*[\'"](.+?)[\'"]\s*\)', response.text)
    if match:
        subid = match.group(1)
        title = match.group(2)
        return title, subid

    title_match = re.search(r'<title>(.*?) sur Steam</title>', response.text)
    title = title_match.group(1).strip() if title_match else f"AppID {appid}"

    subid_match = re.search(r'AddFreeLicense\(\s*(\d+),', response.text)
    subid = subid_match.group(1) if subid_match else None

    return title, subid

def ajouter_jeu(subid):
    url = f"https://store.steampowered.com/freelicense/addfreelicense/{subid}"
    data = {
        "ajax": "true",
        "sessionid": cookies['sessionid']
    }

    response = requests.post(url, headers=headers, cookies=cookies, data=data)
    print(f"📨 Ajout SubID {subid} → Status {response.status_code}")
    print(f"🔍 Réponse : {response.text[:300]}...\n")

    if response.status_code == 200:
        if response.text.strip() == "[]":
            return True, response
        try:
            json_data = json.loads(response.text)
            if "purchaseresultdetail" in json_data:
                if json_data["purchaseresultdetail"] == 9:
                    print("ℹ️ Jeu déjà dans la bibliothèque.")
                    return True, response
                elif json_data["purchaseresultdetail"] == 53:
                    print("🚫 Trop d’activations récentes (code 53).")
        except Exception:
            pass
    return False, response


# Traitement
appids = extraire_appids(fichier_entree)
print(f"🔍 {len(appids)} AppIDs extraits.\n")

with open(fichier_sortie, "w", encoding="utf-8", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["AppID", "Title", "SubID"])

    for appid in appids:
        print(f"➡️ Traitement AppID {appid}")
        title, subid = trouver_subid_et_titre(appid)
        if subid:
            print(f"✅ {title} → SubID {subid}")
            writer.writerow([appid, title, subid])

            success, response = ajouter_jeu(subid)
            if success:
                print(f"🎉 Ajouté à la bibliothèque !\n")
                time.sleep(120)
            else:
                print(f"❌ Échec de l'ajout pour {title}\n")

            # Délai uniquement si Steam a répondu avec purchaseresultdetail
            try:
                last_json = json.loads(response.text)
                if "purchaseresultdetail" in last_json:
                    print("⏳ Délai anti-spam Steam (code présent), pause 60 secondes...\n")
                    time.sleep(200)
            except Exception:
                pass


        else:
            print(f"⚠️ Aucun subid trouvé pour AppID {appid} — passage immédiat.\n")

print(f"\n✅ Extraction + ajout terminé. Résultats dans {fichier_sortie}")
