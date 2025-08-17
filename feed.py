from feedgen.feed import FeedGenerator
import os

class EroFeed:
    def __init__(self):
        fg = FeedGenerator()
        fg.load_extension('podcast')
        fg.id('http://www.ank.com/audio/ero')
        fg.title('Simply Erotic')
        fg.author( {'name': 'Literotica', 'email': 'kevin@ank.com' })
        fg.subtitle("Selected works of Literotica formatted for audio playback")
        fg.link( href="http://www.ank.com/ero.atom")
        fg.language('en')
        fg.podcast.itunes_category('Fiction', 'Erotica')
        fg.podcast.itunes_explicit("yes")
        self.fg = fg

    def add_entry(self, epid, title, desc, size, link=None):
        print("Title:", title)
        print("Description:", desc)
        if link is None: link = epid
        fe = self.fg.add_entry()
        fe.id(epid)
        fe.title(title)
        # fe.link(href=link)
        fe.description(desc)
        fe.enclosure(link, str(size), 'audio/mpeg')

    def save(self):
        self.fg.rss_str(pretty=True)
        self.fg.rss_file('ero.atom')

def scan(basedir, ero, story=""):
    part = 1
    mp3s = []
    with os.scandir(basedir) as it:
        for entry in it:
            if entry.is_dir():
                subdir = basedir + "/" + entry.name
                story = entry.name
                print(f"Scanning {subdir}")
                scan(subdir, ero, story)
            elif entry.is_file() and entry.name.endswith(".mp3"):
                path = basedir + "/" + entry.name
                url = f"http://www.ank.com/audio/{story}/{entry.name}"
                mp3s.append({ 'url': url, 'path': path, 'story': story})

        parts = len(mp3s)
        for mp3 in mp3s:
                url = mp3['url']
                path = mp3['path']
                story = mp3['story']
                title = f"{story} ({part} of {parts})"
                print(f" - Adding {title}")
                size = os.path.getsize(path)
                ero.add_entry(url, title, path, size)
                part += 1

def main(argv):
    flist = argv[1]
    ero = EroFeed()
    with open(flist, "rt") as f:
        while True:
            url = f.readline()
            if not url: break
            url = url.strip('\n')
            title = os.path.basename(url)
            scan(f"audio/{title}", ero, title)
    ero.save()


def bar():
    ero = EroFeed()
    scan("audio", ero)
    ero.save()




if __name__ == "__main__":
    import sys
    main(sys.argv)
