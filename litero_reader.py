from turtle import down
from litero.litero import Litero
from litero.story import Story
import getopt
import sys
import os
import re
from distutils.dir_util import copy_tree
import pathlib

def normalize_title(title):
    path = re.sub(r".txt", "", os.path.basename(title)).lower()
    path = path.replace(' ', '-').replace('!', '').replace(':', '').replace(',','').lower()
    return path

def read_story(story : Story, voice, download_only):
    """ - Load a story as text and turn it into an MP3 using AWS Polly

    story :Story: Reference to a story
    voice :str: Amy, Emma, Ivy, Joanna, Kendra, Kimberly, Sally, Joey, Justin, Kevin, Matthew
                Geraint, Ayanda, Nicole, Olivia, Russell, Aditi, Raveena, Aria
    download_only :bool: Fetches the completed MP3 from AWS without starting a new Polly job
    """
    lit_client = Litero(story, voice=voice)
    ok = os.path.isdir(story.get_audio_path())
    if not ok:
        if not download_only:
            lit_client.read()
        ok = lit_client.download()
    if not ok:
        print("Retry download in a few minutes with the following command:")
        print(f"python {sys.argv[0]} {story.chapter_ref}")
    else:
        audio_path = story.get_audio_path()
        normalized_title = story.get_normalized_title()
        cmd = f"cp -a {audio_path}/ //balrog/www/audio/"
        print(cmd)
        copy_tree(f'{audio_path}', f'//balrog/www/audio/{normalized_title}')


def usage(app):
        print(f"Usage: python {app} [-r] [-v <voice>] [<story-title>|<list-of-titles-file.txt>|<directory-of-stories>]")
        print("   -r : Run the reading job.  Defaults to off, which only downloads a previous reading.")
        print("   -v : Select voice, default 'Brian'")
        print("        (en-GB): Amy, Emma")
        print("        (en-US): Ivy, Joanna, Kendra, Kimberly, Sally, Joey, Justin, Kevin, Matthew")
        print("        (en-GB-WLS): Geraint")
        print("        (en-ZA): Ayanda")
        print("        (en-AU): Nicole, Olivia, Russell")
        print("        (en-IN): Aditi, Raveena")
        print("        (en-NZ): Aria")
        sys.exit(1)

def main(argv):
    app = argv[0]
    download_only = True
    story = None
    voice = None
    stories = []

    try:
        args = argv[1:]
        opts, args = getopt.getopt(args, "rv:")
        opts = dict(opts)
        # print("opts", opts)
        if '-r' in opts: download_only = False
        if '-v' in opts: voice = opts['-v']
        if len(args) < 1: raise Exception("need argument")
    except:
        usage(app)

    if len(args)==1 and os.path.isfile(args[0]):
        with open(args[0], 'rt') as f:
            stories = f.read().split('\n')
    elif len(args)==1 and os.path.isdir(args[0]):
        basedir = pathlib.Path(args[0])
        for path in basedir.glob("**/*.txt"):
            path = str(path)
            if path.endswith(".txt"):
                stories.append(path)
                print(path)
    else:
        stories = args

    for chapter_ref in stories:
        story = Story(chapter_ref)
        read_story(story, voice, download_only)


if __name__ == "__main__":
    main(sys.argv)

