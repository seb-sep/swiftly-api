from openai import AsyncOpenAI
import os
import io
from platform import system
import asyncio

if system() == 'Darwin':
    from dotenv import load_dotenv
    load_dotenv()

# setup opnenai api key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI()

async def transcribe_audio(audio_bytes: io.BytesIO) -> str:
    '''Transcribe the given audio file to text.'''
    print('transcribing audio')

    transcript = await client.audio.transcriptions.create(
        model='whisper-1', 
        file=audio_bytes,
        response_format='text')
    return transcript.strip()

async def test():
    with open('../test.mp3', 'rb') as audio_file:
        transcription = await transcribe_audio(audio_file)
        print(transcription)

if __name__ == '__main__':
    asyncio.run(test())
