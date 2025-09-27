import os
import re
from enum import Enum
import yaml

class StoryRefType(Enum):
    LOCALFILE = 1
    LITERO = 2

class Story:
    """
    Represents a story, complete with multiple chapters and pages.
    """
    def __init__(self, story_ref):
        """
        Args:
            story_ref:dict: A JSON object representing the story.  A list of chapter urls is required, other elements are optional.
                { "title": "Story Title", 
                  "author": "Author Name", 
                  "chapters": [ "url1", "url2", ... ] }

        Chapter references can be either URLs or local file paths.  If a story has only one chapter, it can be specified as a 
        string instead of a list.  A story can also be specified as a single string, which is interpreted as a single chapter URL with
        the title matching the chapter name.
        """

        assert isinstance(story_ref, (dict, str)), f"story_ref must be a dict or a string, not {type(story_ref)}"
        self.chapter = 1
        if type(story_ref) is dict:
            self.story_ref = story_ref
        else:
            self.story_ref = { 'chapters': story_ref }

    def __repr__(self):
        return self.get_normalized_title()

    @property
    def reftype(self):
        if self.chapter_ref.endswith(".txt"):
            return StoryRefType.LOCALFILE
        else:
            return StoryRefType.LITERO

    def next_chapter(self):
        """Advances to the next chapter."""
        self.chapter += 1

    @property
    def chapter_ref(self):
        """Returns the current chapter reference (URL or local file path)."""
        return self.story_ref["chapters"][self.chapter-1]

    def get_normalized_title(self):
        """Generates a title suitable for use in a file path or an S3 key."""
        #print(self.story_ref)
        chapters = self.story_ref['chapters']

        path = re.sub(r".txt", "", os.path.basename(chapters[0])).lower()
        path = path.replace(' ', '-').lower()
        path = re.sub(r"[^a-z0-9-]", "", path, count=1000)
        return path

    def get_audio_path(self):
        """Returns the local path to the audio files for this story."""
        path = f"./audio/{self.get_normalized_title()}"
        return path

    def get_html_path(self):
        """Returns the local path to the HTML file for this story."""
        path = f"./html/{self.get_normalized_title()}.html"
        return path

    def get_s3_path(self, part):
        """Returns the S3 path to the audio files for a part of this story.  Parts are split by text length to fit Polly limits."""
        path = f'{self.get_s3_basepath()}/part{part}'
        return path

    def get_s3_basepath(self):
        """Returns the S3 base path to the audio files for this story."""
        path = f'lite/{self.get_normalized_title()}'
        return path

    def get_title(self):
        """Returns the story title in a human-readable format."""
        if 'title' in self.story_ref:
            title = self.story_ref['title']
        else:
            title = self.get_normalized_title().replace('-', ' ').title()
        return title

class Stories:
    """
    Represents a collection of stories.
    """
    def __init__(self, yaml_file):
        """
        Args:
            yaml_file: A path to a YAML file representing the collection of stories.
        """
        with open(yaml_file, 'rt') as f:
            self.stories_ref = yaml.safe_load(f)
        self.stories_index = {
            story.get_title(): story for story in self.get_stories()
        }

    def __repr__(self):
        return f"Stories({len(self.stories_ref['stories'])} stories)"

    def get_stories(self):
        """Returns a list of Story objects."""
        result = []
        for story_ref in self.stories_ref['stories']:
            story = Story(story_ref)
            result.append(story)
        return result
    
    def get_story(self, title):
        """Returns a Story object by title."""
        if title in self.stories_index:
            return self.stories_index[title]
        return None
    
    def get_titles(self):
        """Returns a list of story titles."""
        return list(self.stories_index.keys())
    
    def dir(self):
        """Prints a list of stories."""
        for i, title in enumerate(self.get_titles()):
            print(f"{i + 1:2d}: {title}")