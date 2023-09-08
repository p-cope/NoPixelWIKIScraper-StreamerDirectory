from bs4 import BeautifulSoup as BS
import requests
from main import sanitize_wiki_link

member_words = ['member','og','mdma','leader','hangaround','associate','shinobi','full','prospect','shotcaller','blooded','prime minister',
                'vice prime minister','command','captain','king','enforcer','goon','g 1','g 2','g 3','lord','boss','president','sergeant',
                'chaplain','nomad','soldier','elder','treasurer','secretary','quartermaster','veteran','jefe','capitain','soldado',
                'ambassador','milf','scrapling','naked','council','founder','gangster','baby','huntsman','curator','sgt','oracle',
                'patched','sicario','oyabun','wakagashira','shateigashira','hashira','shingiin','adobaiza','komon','isha','kumi','mikomi','butler',
                'mechanic']

excluded_member_words = ['honourary','honorary','retired','inactive']

twitch_link_words = ['played','twitch']

names = []


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

    return cleaned_role.strip()


def get_twitch_from_url(url):

    html = get_html(url)
    aside = html.find_all('aside')[0]

    h3s = aside.find_all('h3', string=lambda text: any(word in (text or '').lower() for word in twitch_link_words))

    for h3 in h3s:

        parent_div = h3.find_parent('div')
        a_tag = parent_div.find('a')

        if a_tag:

            if ('twitch' in a_tag['href']):
                return a_tag['href']
            
            elif ('kick' in a_tag['href']):     #recursion is too slow in python
                return a_tag['href']
        
            elif ('wiki' in a_tag['href']):

                return get_twitch_from_url(sanitize_wiki_link(a_tag['href']))
                
            else:
                return '' #figure out a method for the people it doesn't work for
        
        else:
            return ''   


def get_members_from_html(html):

    members = []
    members_set = set() #avoiding duplicate entries

    aside = html.find_all('aside')[0]

    h3s = aside.find_all('h3', string=lambda text: any(word in (text or '').lower() for word in member_words) and not any(excluded_word in (text or '') for excluded_word in excluded_member_words)) #(text or '') is essential else it throws a fit at NoneTypes
    
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
