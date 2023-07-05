import requests
from bs4 import BeautifulSoup
import os
import urllib.parse

   
def format_filename(name):
    result = "".join([c for c in name if c.isalpha() or c.isdigit() or c in [' ', '(', ')']]).rstrip()
    return result.strip()

def get_metas(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    meta = {}

    title = soup.find('h1', {'itemprop':'name'}).findChild().text
    meta['title'] = title
    meta['filename'] = format_filename(title)
    
    author = soup.find('h2', {'itemprop':'author'}).findChild().findChild().text
    meta['author'] = author

    desc = soup.find('p').text
    meta['desc'] = desc

    meta['chapters'] = []
    anchor = soup.find('h5')
    for sibling in anchor.next_siblings:
        if sibling.name == 'p':
            if not sibling.has_attr('style'):
                a = sibling.find('a')
                if not a:
                    continue
                chp ={
                    'href' : urllib.parse.urljoin(url, a['href']),
                    'title':a.text
                }
                meta['chapters'].append(chp)

    return meta

def get_chapter(filename, url, onepage):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html5lib')
    
    anchor = soup.find('h4')
    title = anchor.text

    content = []
    for sibling in anchor.next_siblings:
        if sibling.name == 'p':
            img = sibling.find('img')
            if not img:
                content.append(sibling.text)

    content = '\n\n'.join(content)
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        file.write(f"{title}\n\n")
        file.write(f"{content}\n\n")
    
    with open(onepage, 'a', newline='', encoding='utf-8') as file:
        file.write(f"{title}\n\n")
        file.write(f"{content}\n\n")
        file.write(f"{'='*56}\n\n\n")

    print(f'done : {filename:<20}')
    return

def scraper(url):
    meta = get_metas(url)
    chps = meta['chapters']
    path = f'./{meta["filename"]}/'
    onepage = f'{path}{meta["filename"]}.txt'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(onepage, 'w', newline='', encoding='utf-8') as file:
        file.write(f"{str(meta['title'])}\n\n")
        file.write(f"{str(meta['author'])}\n\n")
        file.write(f"{str(meta['desc'])}\n\n")

        file.write(f"{'='*56}\n\n\n")
    
    # filename = f'{path}{1:03d}. {chps[0]["title"]}.txt'
    # get_chapter(filename, chps[0]['href'], onepage)

    for i, chp in enumerate(chps):
        filename = f'{path}{i+1:03d}. {chp["title"]}.txt'
        get_chapter(filename, chp['href'], onepage)

    with open(f'{path}chapter-list.txt', 'w', newline='', encoding='utf-8') as file:
        file.write(f'{str(meta["title"])}\n')
        for a_tag in meta["chapters"]:
            file.write(f"{str(a_tag)}\n")
        
    
    print(f'done : total {i+1} files')

def get_targets():
    urls = []
    with open('targets.txt', 'r', newline='', encoding='utf-8') as file:
        for line in file:
            urls.append(line.rstrip())
    return urls

if __name__ == '__main__':
    urls = get_targets()
    for url in urls:
        # scarpe each fiction
        scraper(url) 

