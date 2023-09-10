from bs4 import BeautifulSoup as BS
import requests
import re

member_words = ['member','og','mdma','leader','hangaround','associate','shinobi','full','prospect','shotcaller','blooded','prime minister',
                'vice prime minister','command','captain','king','enforcer','goon','g 1','g 2','g 3','lord','boss','president','sergeant',
                'chaplain','nomad','soldier','elder','treasurer','secretary','quartermaster','veteran','jefe','capitain','soldado',
                'ambassador','milf','scrapling','naked','council','founder','gangster','baby','huntsman','curator','sgt','oracle',
                'patched','sicario','oyabun','wakagashira','shateigashira','hashira','shingiin','adobaiza','komon','isha','kumi','mikomi','butler',
                'mechanic','sheriff','corporal','deputy','cadet','lieutenant','chief','officer','trooper','warden','ranger','doctor','mayor',
                'justice','judge','clerk','commissioner','paramedic','emt','trainee','supervisor','detective','director','attorney','admin',
                'attending','therapist','resident','intern','nurse']

excluded_member_words = ['honourary','honorary','retired','inactive','branch']

twitch_link_words = ['played','twitch']

names = []


def sanitize_wiki_link(url):

    if 'http' in url:
        return url
    else:
        return 'https://nopixel.fandom.com' + url
    

def get_html(url):

    page = requests.get(url)
    soup = BS(page.content, 'html.parser')

    return soup


def clean_role(role):

    cleaned_role = ''
    index = 0

    for char in role:

        if not char.isnumeric() or index < 3: cleaned_role += char
        index += 1

    return cleaned_role.strip().lower()


def get_twitch_from_url(url):

    if 'wiki' in url:
        html = get_html(url)
    else:
        return ''

    try:
        aside = html.find_all('aside')[0]
    except IndexError:
        print(f"Failed to process URL: {url}")
        return ''

    h3s = aside.find_all('h3', string=lambda text: any(word in (text or '').lower() for word in twitch_link_words))

    for h3 in h3s:

        h3parent_div = h3.find_parent('div')
        h3a_tag = h3parent_div.find('a')

        if h3a_tag:

            if ('twitch' in h3a_tag['href']):
                return h3a_tag['href']
            
            elif ('kick' in h3a_tag['href']):     #recursion is too slow in python
                return h3a_tag['href']
        
            elif ('wiki' in h3a_tag['href']):

                return get_twitch_from_url(sanitize_wiki_link(h3a_tag['href']))
    
    pa_tag = None

    for tag in html.find_all(string=re.compile(r"played by", re.I)):

        next_tag = tag.find_next()

        if next_tag and next_tag.name == 'a':
            pa_tag = next_tag

    if pa_tag:

            if ('twitch' in pa_tag['href']):
                return pa_tag['href']
            
            elif ('kick' in pa_tag['href']):     #recursion is too slow in python
                return pa_tag['href']
        
            elif ('wiki' in pa_tag['href'] and not 'wikia' in pa_tag['href']):

                return get_twitch_from_url(sanitize_wiki_link(pa_tag['href']))
    
    return ''


def get_members_from_html(html):

    members = []
    members_set = set() #avoiding duplicate entries

    aside = html.find_all('aside')[0]

    h3s = aside.find_all('h3', string=lambda text: any(word in (text or '').lower() for word in member_words) and not any(excluded_word in (text or '').lower() for excluded_word in excluded_member_words)) #(text or '') is essential else it throws a fit at NoneTypes
    
    for line in h3s:

        parent_div = line.find_parent('div')
        member_name_tag = parent_div.find('a')
        if (member_name_tag and (member_name_tag.text not in members_set)):
            
            link = sanitize_wiki_link(member_name_tag['href'])
            
            members.append((member_name_tag.text, clean_role(line.text), link, get_twitch_from_url(link)))
            members_set.add(member_name_tag.text)   #need to implement a fix for when there are several people in one box-- the GSF problem!
    
    return members


def url_to_members(url):

    html = get_html(url)
    member_list = get_members_from_html(html)

    return member_list