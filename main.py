from bs4 import BeautifulSoup as BS
import requests, sqlite3, members_scrape
from alive_progress import alive_bar

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

active_gov = [("PBSO", "/wiki/Paleto_Bay_Sheriff%27s_Office"),("SDSO", "/wiki/Senora_Desert_Sheriff%27s_Office"),("LSPD", "/wiki/Los_Santos_Police_Department"),
                          ("SASP", "/wiki/San_Andreas_State_Police"),("SASPR", "/wiki/San_Andreas_State_Park_Rangers"),("DOC", "/wiki/Department_of_Corrections"),
                          ("DOJ", "/wiki/Department_of_Justice"),("EMS", "/wiki/Emergency_Medical_Services"),("MCU", "/wiki/Major_Crimes_Unit"),("LSMG", "/wiki/Los_Santos_Medical_Group"),
                          ("HSPU", "/wiki/High_Speed_Pursuit_Unit")]

GANG_DIR_URL = 'https://nopixel.fandom.com/wiki/Category:Gangs'
GANG_DIR_URL_2 = 'https://nopixel.fandom.com/wiki/Category:Gangs?from=Seaside'
RACING_DIR_URL = 'https://nopixel.fandom.com/wiki/Category:Racing_Crew'

def find_each_group_from_directory(url):

    page = requests.get(url)
    soup = BS(page.content, 'html.parser')
    
    return soup.find_all(class_ = "category-page__member-link")

gangs_unref = find_each_group_from_directory(GANG_DIR_URL)
gangs_unref_p2 = find_each_group_from_directory(GANG_DIR_URL_2)
racing_unref = find_each_group_from_directory(RACING_DIR_URL)

groups_unref = gangs_unref + gangs_unref_p2 + racing_unref
group_names = []
group_links = []

anon_no = 0

def get_streamer_name_from_link(url):
    global anon_no
    
    if url:
        return (url.rstrip('/').split('/')[-1]).lower()
    else:
        anon_no += 1
        return 'anon' + str(anon_no)


for line in groups_unref:

    item_title = line.get('title')

    if ((not 'Template' in item_title) and ( not 'Category' in item_title) and (not '2.0' in item_title) and (not 'members' in item_title.lower()) and ('/' not in item_title) and (not item_title in group_names)):

        group_names.append(item_title)
        group_links.append(members_scrape.sanitize_wiki_link(line.get('href')))


for dep in active_gov:

    group_names.append(dep[0])
    group_links.append(members_scrape.sanitize_wiki_link(dep[1]))


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
               link TEXT UNIQUE,
               people_live INTEGER NOT NULL,
               people_on_gta INTEGER NOT NULL);
               ''')

cursor.execute('''
               CREATE TABLE streamers (
               streamer_id INTEGER PRIMARY KEY,
               streamer_name TEXT UNIQUE,
               streamer_link TEXT,
               streamer_is_live INTEGER NOT NULL CHECK(streamer_is_live IN (0, 1)),
               streamer_on_gta INTEGER NOT NULL CHECK(streamer_is_live IN (0, 1)));
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
               member_gang_id INTEGER REFERENCES gangs(id),
               member_role TEXT
               );
               ''')


for i in range(group_quantity):
    cursor.execute("INSERT INTO gangs (name, link, people_live, people_on_gta) VALUES (?, ?, 0, 0)", (group_names[i], group_links[i]))

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

print()

with alive_bar(len(all_gangs), title="Gathering Wiki Info and Inserting Into Tables") as bar:
    for gang in all_gangs:

        gang_name = gang[0]
        gang_link = gang[1]
        clean_gang_name = sanitize(gang_name)
        members_list = members_scrape.url_to_members(gang_link)

        for character in members_list:
        
            cursor.execute('SELECT id FROM gangs WHERE name = ?', (gang_name,))
            gang_id = cursor.fetchone()[0]


            cursor.execute('INSERT OR IGNORE INTO streamers (streamer_name, streamer_link, streamer_is_live, streamer_on_gta) VALUES (?, ?, 0, 0)', (get_streamer_name_from_link(character[3]), character[3]))
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

            cursor.execute('INSERT INTO character_gang_link (member_character_id, member_gang_id, member_role) VALUES (?, ?, ?)', (character_id, gang_id, character[1]))                                                                                                                             

        bar()

cursor.execute('''DELETE FROM gangs WHERE id NOT IN (SELECT DISTINCT member_gang_id FROM character_gang_link)''')
print()

conn.commit()