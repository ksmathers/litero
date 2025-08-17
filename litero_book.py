from litero.litero import Litero
from litero.story import Story
import getopt
import sys
import os
import re
from distutils.dir_util import copy_tree
import pathlib
import yaml

def normalize_title(title):
    path = re.sub(r".txt", "", os.path.basename(title)).lower()
    path = path.replace(' ', '-').replace('!', '').replace(':', '').replace(',','').lower()
    return path

def save_story(story : Story):
    """ - Load a story as text and turn it into an MP3 using AWS Polly

    story :Story: Reference to a story
    """
    lit_client = Litero(story)
    output_file = story.get_html_path()
    if os.path.isfile(output_file):
        print(f"skipping {output_file}: already exists")
        return
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    body = lit_client.get_full_story_html()
    body = body.encode('utf-8', errors='ignore')
    with open(output_file, "wb") as f:
        f.write(body)

def usage(app):
        print(f"Usage: python {app} <story-def.yaml>")
        sys.exit(1)

def main(argv):
    app = argv[0]
    download_only = True
    story = None
    voice = None
    stories = []

    try:
        args = argv[1:]
        if len(args) < 1: raise Exception("need argument")
    except:
        usage(app)

    if len(args)==1 and os.path.isfile(args[0]):
        with open(args[0], 'rt') as f:
            stories = yaml.load(f, yaml.loader.SafeLoader)
    else:
        usage(app)

    for story_def in stories['stories']:
        story_ref = story_def['chapters']
        story = Story(story_ref)
        save_story(story)


if __name__ == "__main__":
    main(sys.argv)

