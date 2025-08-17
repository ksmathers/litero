import os
import re
from enum import Enum

class StoryRefType(Enum):
    LOCALFILE = 1
    LITERO = 2

class Story:
    def __init__(self, story_ref):
        self.chapter = 1
        if type(story_ref) is list:
            self.story_ref = story_ref
        else:
            self.story_ref = [ story_ref ]

    def __repr__(self):
        return self.get_normalized_title()

    @property
    def reftype(self):
        if self.chapter_ref.endswith(".txt"):
            return StoryRefType.LOCALFILE
        else:
            return StoryRefType.LITERO

    def next_chapter(self):
        self.chapter += 1

    @property
    def chapter_ref(self):
        return self.story_ref[self.chapter-1]

    def get_normalized_title(self):
        path = re.sub(r".txt", "", os.path.basename(self.story_ref[0])).lower()
        path = path.replace(' ', '-').lower()
        path = re.sub(r"[^a-z0-9-]", "", path, count=1000)
        return path

    def get_audio_path(self):
        path = f"./audio/{self.get_normalized_title()}"
        return path

    def get_html_path(self):
        path = f"./html/{self.get_normalized_title()}.html"
        return path

    def get_s3_path(self, part):
        path = f'{self.get_s3_basepath()}/part{part}'
        return path

    def get_s3_basepath(self):
        path = f'lite/{self.get_normalized_title()}'
        return path

    def get_title(self):
        path = self.get_normalized_title().replace('-', ' ')
        return path

