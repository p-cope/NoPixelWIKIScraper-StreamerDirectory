from bs4 import BeautifulSoup as BS
import requests
import sqlite3
import members_scrape

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

GANG_PAGE_URL = 'https://nopixel.fandom.com/wiki/Category:Gangs'
GANG_PAGE_URL_2 = 'https://nopixel.fandom.com/wiki/Category:Gangs?from=Seaside'
RACING_CREW_URL = 'https://nopixel.fandom.com/wiki/Category:Racing_Crew'

def find_each_group_from_directory(url):

    page = requests.get(url)
    soup = BS(page.content, 'html.parser')
    
    return soup.find_all(class_ = "category-page__member-link")

gangs_unref = find_each_group_from_directory(GANG_PAGE_URL)
gangs_unref_p2 = find_each_group_from_directory(GANG_PAGE_URL_2)
racing_unref = find_each_group_from_directory(RACING_CREW_URL)

groups_unref = gangs_unref + gangs_unref_p2 + racing_unref
group_names = []
group_links = []


def sanitize_wiki_link(url):

    if 'http' in url:
        return url
    else:
        return 'https://nopixel.fandom.com' + url
    

def get_streamer_name_from_link(url):
    
    if url:
        return url.rstrip('/').split('/')[-1]
    else:
        return url


for line in groups_unref:

    item_title = line.get('title')

    if ((not 'Template' in item_title) and ( not 'Category' in item_title) and (not item_title in group_names)):

        group_names.append(item_title)
        group_links.append(sanitize_wiki_link(line.get('href')))


group_quantity = len(group_names)


conn = sqlite3.connect('gangs_database.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for table in tables:
    cursor.execute(f'DROP TABLE IF EXISTS "{table[0]}"') #drops every table before starting

conn.commit()
cursor.execute("DROP TABLE IF EXISTS gangs")


cursor.execute('''
               CREATE TABLE gangs (
               id INTEGER PRIMARY KEY,
               name TEXT not NULL,
               link TEXT UNIQUE);
               ''')

cursor.execute('''
               CREATE TABLE streamers (
               streamer_id INTEGER PRIMARY KEY,
               streamer_name TEXT UNIQUE,
               streamer_link TEXT UNIQUE);
               ''')

cursor.execute('''
               CREATE TABLE characters (
               character_id INTEGER PRIMARY KEY,
               character_name TEXT not NULL,
               character_link TEXT UNIQUE,
               character_streamer_id INTEGER REFERENCES streamers(id)
               );
               ''')

cursor.execute('''
               CREATE TABLE character_gang_link (
               member_id INTEGER PRIMARY KEY,
               member_character_id INTEGER REFERENCES characters(character_id),
               member_gang_id INTEGER REFERENCES gangs(id)
               );
               ''')


for i in range(group_quantity):
    cursor.execute("INSERT INTO gangs (name, link) VALUES (?, ?)", (group_names[i], group_links[i]))

conn.commit()


def sanitize(name):

    cleanname = ''
    for char in name:
        if char == ' ':
            cleanname += '_'
        elif ((not char == ' ') and char.isalnum()):
            cleanname += char

    return cleanname


cursor.execute("SELECT name, link FROM gangs")
all_gangs = cursor.fetchall()


gang_iter_index = 1
print()


for gang in all_gangs:


    progress = gang_iter_index/group_quantity
    progress_rounded = round(progress * 100)


    gang_name = gang[0]
    gang_link = gang[1]
    clean_gang_name = sanitize(gang_name)
    members_list = members_scrape.url_to_members(gang_link)

    for character in members_list:
        
        cursor.execute('SELECT id FROM gangs WHERE name = ?', (gang_name,))
        gang_id = cursor.fetchone()[0]

        cursor.execute('INSERT OR IGNORE INTO streamers (streamer_name, streamer_link) VALUES (?, ?)', (get_streamer_name_from_link(character[3]), character[3]))
        if cursor.rowcount == 0:
            cursor.execute("SELECT streamer_id FROM streamers WHERE streamer_name = ?", (get_streamer_name_from_link(character[3]),))
            streamer_id = cursor.fetchone()[0]
        else:
            streamer_id = cursor.lastrowid

        cursor.execute('INSERT OR IGNORE INTO characters (character_name, character_link, character_streamer_id) VALUES (?, ?, ?)', (character[0], character[2], streamer_id))
        if cursor.rowcount == 0:
            cursor.execute("SELECT character_id FROM characters WHERE character_link = ?", (character[2],))
            character_id = cursor.fetchone()[0]
        else:
            character_id = cursor.lastrowid

        cursor.execute('INSERT INTO character_gang_link (member_character_id, member_gang_id) VALUES (?, ?)', (character_id, gang_id))                                                                                                                             

    print('   PROGRESS -----> ' + ('⬜' * progress_rounded) + ('⬛' * (100 - progress_rounded)), end = "\r")

    gang_iter_index += 1


print("\n" * 2)
conn.commit()