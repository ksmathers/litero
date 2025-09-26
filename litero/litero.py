

import requests
import re
from bs4 import BeautifulSoup
import keyring
from time import sleep
from .pollyclient import PollyClient
from .story import Story, StoryRefType
import os


CLEANR = re.compile('<.*?>')
def cleanhtml(raw_html):
    """Removes HTML tags from a string."""
    txt = re.sub(CLEANR, '', raw_html)
    return txt

class Litero:
    def __init__(self, story:Story, voice = None):
        self.headers = requests.utils.default_headers()
        self.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36'
        self.base_url = "http://www.literotica.com"
        self.voice = voice
        self.story = story
        print(f"story {story}...")
        if story.reftype == StoryRefType.LOCALFILE:
            story_text = self.get_story_file(story)
        elif story.reftype == StoryRefType.LITERO:
            story_text = self.get_full_story_txt(story)
        else:
            raise Exception(f"Unimplemented ref type {story.reftype}")
        self.polly = PollyClient(story, story_text, voice=self.voice)

    def get(self, url):
        resp = requests.get(url, headers=self.headers)
        print(f"fetch {url} response code {resp.status_code}")
        if resp.status_code != 200:
            raise Exception(f"Unable to fetch url: {url}")
        return resp.content.decode('UTF-8')

    def fetch_story_content(self, story_ref, page=1, textonly=False):
        """Fetches the story from a given story reference and page number as a generator.
        Args:
            story_ref: The URL or local file path of the story chapter.
            page: The page number to fetch.
            textonly: If True, returns plain text; otherwise, returns HTML elements.
        Yields:
            The text or HTML elements of the story.
        """
        if not story_ref.startswith('http'):
            story_ref = self.base_url + "/s/" + story_ref + "?page=" + str(page)
        else:
            story_ref = story_ref + "?page=" + str(page)
        body = self.get(story_ref)
        soup = BeautifulSoup(body, 'html.parser')

        HAS_TEXT = re.compile('[A-Za-z]{3}') # search for at least a 3-letter word to avoid picking up junk

        for e in soup.find_all('div', {'class': 'aa_ht'}):
            for para in e.find_all('p'):
                txt = cleanhtml(str(para))

                if re.search(HAS_TEXT, txt):
                    if textonly:
                        yield txt
                    else:
                        yield para

    def get_story_html(self, chapter):
        """Fetches the HTML content of a story chapter."""
        result = f"<h1>Chapter {chapter}</h1>\n"
        for i in range(100): # limit to 100 pages per chapter in case of bugs
            try:
                page = i+1
                otxt = ""
                for p in self.fetch_story_content(self.story.chapter_ref, page, textonly=False):
                    otxt += f"<p>{p}</p>\n"
                result += f"<h2>Page {page}</h2>\n{otxt}\n"
            except:
                break
        result += "\n"
        return result

    def get_full_story_html(self):
        """Fetches the full story as HTML."""
        body = ""
        for i in range(len(self.story.story_ref)):
            body += self.get_story_html(i)
            self.story.next_chapter()
        return body

    def get_story_text(self, story, page=1):
        """
        Fetches the story as ASCII text for a specific page.
        """
        return self.fetch_story_content(story, page, textonly=True)

    def get_full_story_ssml(self, story):
        """
        Fetches the full story as speech synthesis markup language (SSML).

        Args:
            story: The Story object representing the story to fetch.
        Returns:
            The full story in SSML format
        """
        ssml="<speak>\n"
        for i in range(100):
            try:
                if i > 0:
                    ssml += f'<break time="1500ms">\n'
                page = i+1
                ssml += f'Page {page}<break time="1000ms">\n'
                for p in self.get_story(story, page):
                    ssml += p
                    ssml += f'<p>\n'
            except:
                break
        ssml += "</speak>\n"
        return ssml

    def get_full_story_txt(self, story : Story):
        """
        Fetches the full story as plain text, split into parts to fit Polly limits.
        
        Args:
            story: The Story object representing the story to fetch.
        Yields:
            Parts of the story as plain text, each part fitting within Polly's limits.
        """
        fulltext=""
        for i in range(100):
            try:
                if i > 0:
                    fulltext += f'\n\n'
                page = i+1
                header = f'Page {page}\n\n'
                for p in self.get_story_text(story.chapter_ref, page):
                    if not header is None:
                        fulltext += header
                        header = None
                    fulltext += p
                    fulltext += f'\n\n'
                if len(fulltext)>80000:
                    yield fulltext
                    fulltext=""
            except Exception as ex:
                print(ex)
                break
        fulltext += "\n"
        yield fulltext

    def get_story_file(self, story : Story):
        #print("get_story_file()")

        ssml = story.get_title() + "\n\n"
        eof = False
        with open(story.chapter_ref, "rt") as f:
            while not eof:
                ll = f.readline()
                #print(f"ll={ll}")
                if not ll:
                    eof=True
                else:
                    ssml += ll
                if (len(ssml)>80000 and ll=="\n") or eof:
                    print(f"get_story_file -> [{len(ssml)}]{ssml[0:60]}... ")
                    yield ssml
                    ssml = ""


    def read(self):
        print('Reading')
        self.polly.read()
        sleep(5)

    def download(self):
        print(f'Downloading story {self.story.chapter_ref}')
        count = 0
        while self.polly.download():
            print('...')
            sleep(5)
            count += 1
            if count >= 30:
                print("Timed out")
                return False
        return True
