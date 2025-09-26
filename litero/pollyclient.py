import boto3
import os
import re
import keyring
from .story import Story
from typing import List
from multicloud.backend.secret import Secret 


class PollyClient:
    def __init__(self, story : Story, story_text : List[str], voice : str = None):
        language = 'en-GB'
        if voice is None:
            voice = 'Brian'

        if voice in ['Brian', 'Amy', 'Emma']:
            language = 'en-GB'
        elif voice in ['Ivy', 'Joanna', 'Kendra', 'Kimberly', 'Sally', 'Joey', 'Justin', 'Kevin', 'Matthew']:
            language = 'en-US'
        elif voice in ['Geraint']:
            language = 'en-GB-WLS'
        elif voice in ['Ayanda']:
            language = 'en-ZA'
        elif voice in ['Nicole', 'Olivia', 'Russell']:
            language = 'en-AU'
        elif voice in ['Aditi', 'Raveena']:
            language = 'en-IN'
        elif voice in ['Aria']:
            language = 'en-NZ'
        else:
            raise Exception(f"Unknown voice {voice}")

        self.story_text = story_text
        self.story = story
        self.voice = voice
        self.language = language
        self.parts = 0



    def read(self, secret: Secret):
        print("read()")
        creds = secret.get()
        assert 'access_id' in creds, "Secret must contain access_id"
        assert 'secret_key' in creds, "Secret must contain secret_key"

        polly = boto3.client('polly',
             aws_access_key_id=creds['access_id'],
             aws_secret_access_key=creds['secret_key'],
             region_name='us-west-2')
        
        res=[]
        part = 0
        for i,txt in enumerate(self.story_text):
            part += 1
            r = polly.start_speech_synthesis_task(
                Engine='standard',  #neural
                LanguageCode=self.language,
                OutputFormat='mp3',
                OutputS3BucketName='frubious-bandersnatch',
                OutputS3KeyPrefix=self.story.get_s3_path(part),
                SampleRate='22050',
                # SnsTopicArn
                # SpeechMarkTypes='ssml',
                Text=txt,
                TextType='text',
                VoiceId=self.voice
            )
            #print(f"part {i} len {len(txt)}") # result {r}")
            print('part',i,'length',len(txt))


    def download(self, basedir="."):
        """
        Downloads the audio files for this story from S3, if they exist.
        Return True as long as the files are not yet ready. 
        Returns False if the files are present, in which case they are downloaded.
        """
        try_again = True
        s3 = boto3.client('s3',
             aws_access_key_id=keyring.get_password('aws','access_id'),
             aws_secret_access_key=keyring.get_password('aws', 'secret_key'))
        res = s3.list_objects_v2(
            Bucket='frubious-bandersnatch',
            Prefix=self.story.get_s3_basepath()+"/",
            Delimiter='/'
        )
        print(res)
        if not 'Contents' in res:
            return try_again
        if len(res['Contents']) < self.parts:
            return try_again

        # All parts are present, download them
        try_again = False
        destdir = self.story.get_audio_path()
        if not os.path.isdir(destdir):
            os.mkdir(destdir)

        for itm in res['Contents']:
            if itm['Key'] == "": continue
            key = itm['Key']
            print(f"Downloading '{key}'")
            fname = os.path.basename(key).split('.')
            fname = f"{fname[0]}.mp3"
            s3.download_file('frubious-bandersnatch', key, f"{destdir}/{fname}")

        return try_again