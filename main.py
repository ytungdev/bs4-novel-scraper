from bs4 import BeautifulSoup
import os
import time
import json
import sys

from selenium import webdriver
from selenium_stealth import stealth


class TargetsLoader:
    def __init__(self, file='targets.txt'):
        self.__data = []
        with open(file, newline='') as f:
            for line in f:
                row = line.strip().split(",")
                if len(row) == 2:
                    self.__data.append(row)
                elif len(row) == 1:
                    self.__data.append([row[0], 0])

    def list(self):
        return self.__data


class Scrapper():
    def __init__(self, driver, max_attempt=5, output_dir='./output'):
        self.driver = driver
        self.max_attempt = max_attempt
        self.output_dir = output_dir

    def format_filename(self, name):
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in [' ', '(', ')']]).rstrip()


class Checker:
    def __init__(self, ref='targets.bak.txt'):
        self.ref = ref

        with open(self.ref, 'r') as file:
            lines = file.read()
            lines = lines.splitlines()
        self.idx = lines

    def is_new(self, url):
        return url not in self.idx


class Logger:
    def __init__(self, logfile='targets.bak.txt'):
        self.logfile = logfile

    def log(self, url):
        with open(self.logfile, 'a') as file:
            file.write(f"{url}\n")
        print("\u2937 logged book")


class BookMetaScrapper(Scrapper):
    def __init__(self, driver, url, max_attempt=5, output_dir="./output"):
        super().__init__(driver, max_attempt, output_dir)
        self.book_url = url

    def get_meta(self):
        attempt = 0
        while attempt < self.max_attempt:
            try:
                meta_file = self.__get_meta()
                return meta_file
            except AttributeError as e:
                print(f"\u2937 Attempt {attempt}/{self.max_attempt} : {e} -- retry")
                attempt += 1
                continue
        print(f"\u2937 Attempt {attempt}/{self.max_attempt} : get_meta() Max attempt reached -- abort\n\n")
        sys.exit()
        return False

    def __get_meta(self):
        self.driver.get(self.book_url)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        meta = {}

        title = soup.find('span', {'class': 'title'}).text
        title = self.format_filename(title)
        meta['title'] = title
        output_path = os.path.join(self.output_dir, title)
        output_filename = os.path.join(output_path, f'{title}-meta.json')

        meta['book_url'] = self.book_url

        author_span = soup.find('span', {'class': 'author'})
        author_text = author_span.find('a').text
        author = author_text
        meta['author'] = author.rstrip().lstrip()

        description = soup.find('div', {'class': 'description'}).text
        meta['description'] = description.rstrip().lstrip()

        chp_list_ul = soup.find('ul', attrs={'id': 'chapter-list'})
        chp_list_li = chp_list_ul.find_all("li", recursive=False)
        chapters = {}
        id = 0
        for li in chp_list_li:
            a_tag = li.findChildren("a")
            chp = {}
            if a_tag != []:
                chp_href = a_tag[0]['href']
                chp_title = a_tag[0].text
                chp['url'] = f'https:{chp_href}'
                chp['title'] = self.format_filename(chp_title)
                chapters[id] = chp
                id += 1
        meta['length'] = id
        meta['chapters'] = chapters

        # Write meta
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', newline='', encoding='utf-8') as file:
            file.write(json.dumps(meta, indent=4,
                       sort_keys=False, ensure_ascii=False))

        return output_filename


class BookScrapper(Scrapper):
    def __init__(self, driver, meta_file, start=0, section_size=500, max_attempt=5, output_dir="./output"):
        super().__init__(driver, max_attempt, output_dir)
        self.meta_file = meta_file
        self.output_dir = os.path.dirname(meta_file)
        self.start_chapter = start // section_size * section_size
        self.dir_path = os.path.dirname(meta_file)
        with open(meta_file, 'r') as file:
            data = json.load(file)
        self.meta = data
        self.logger = Logger()

    def scrap_book(self):
        attempt = 0
        print(f"-- Book scrapping : {self.meta_file}")
        while attempt < self.max_attempt:
            try:
                self.__scrap_book()
                return
            except AttributeError as e:
                print(f"\u2937 Attempt {attempt}/{self.max_attempt} : {e} -- retry")
                attempt += 1
                time.sleep(0.5)
                continue
        print(f"\u2937 Attempt {attempt}/{self.max_attempt} : Max attempt reached -- abort\n\n")
        sys.exit()
        return False

    def __scrap_book(self):
        chapters = self.meta["chapters"]
        length = self.meta['length']
        for i in range(self.start_chapter, length):
            section = i // 500 + 1
            url = chapters[str(i)]['url']
            section_file = os.path.join(self.output_dir, f"{self.meta['title']}-{section}.txt")
            print(f"    scrapping {i:>4}/{length}: {section_file} : {url}")
            self.scrap_chapter(url, section_file)
        print("\u2937 completed book")
        self.logger.log(self.meta['book_url'])
        

    def scrap_chapter(self, url, section_file):
        attempt = 0
        sleep_time = 0.5
        while attempt < self.max_attempt:
            try:
                self.__scrap_chapter(url, section_file)
                return 
            except AttributeError as e:
                print(f"    \u2937 Attempt {attempt}/{self.max_attempt} : {e} -- retry")
                attempt += 1
                time.sleep(sleep_time)
                sleep_time += 1
                continue
        print(f"    \u2937 Attempt {attempt}/{self.max_attempt} : Max attempt reached -- abort\n\n")
        with open('debug.txt', 'w', newline='', encoding='utf-8') as file:
            file.write(self.driver.current_url)
            file.write(self.driver.page_source)
        sys.exit()
        return False


    def __scrap_chapter(self, url, output_file):
        self.driver.get(url)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        title = soup.find('div', {'class': 'name'}).text
        content = soup.find('div', {'class': 'content'}).text
        # write chapter.txt
        # with open(filename, 'w', newline='', encoding='utf-8') as file:
        #     file.write(f"{str(title)}\n\n")
        #     file.write(f"{str(content)}")

        with open(output_file, 'a', newline='', encoding='utf-8') as file:
            file.write(f"{str(title)}\n\n")
            file.write(f"{str(content)}\n\n")
            file.write(f"{'='*56}\n\n\n")

        print("    \u2937 completed chapter")


if __name__ == '__main__':
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    # options.add_argument("--window-size=1920,1080")
    # options.add_argument("--start-maximized")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    target_txt = 'targets.txt'
    loader = TargetsLoader()
    checker = Checker()
    book_list = loader.list()
    
    for book_url, start in book_list:
        if checker.is_new(book_url):
            meta = BookMetaScrapper(driver, book_url)
            meta_file = meta.get_meta()
            if meta_file:
                print(f"-- meta acquired : {meta_file}")
                scrapper = BookScrapper(driver, meta_file, start=int(start))
                scrapper.scrap_book()

        else:
            print(f"#### book already downloaded : {book_url}")

    # with open(target_txt, 'r', newline='', encoding='utf-8') as file:
    #     for url in file:
    #         scrapper = BookScrapper(url.rstrip())
    #         scrapper.scrap_book()
    #         # scrapper.scrap_book(start=602)
