from openai import AsyncOpenAI
import os
import io
from platform import system
from typing import List

# only import dotenv if running locally
if system() == 'Darwin':
    from dotenv import load_dotenv
    load_dotenv()

# setup opnenai api key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI()

async def transcribe_audio(audio_bytes: io.BytesIO) -> str:
    '''Transcribe the given audio file to text.'''

    transcript = await client.audio.transcriptions.create(
        model='whisper-1', 
        file=audio_bytes,
        response_format='text')
    return transcript.strip()

async def generate_note_title(note: str) -> str:
    '''Generate a title for a note.'''

    completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system", "content": "Write a brief, unique title summarizing the following note in about four words."},
            {"role": "user", "content": note}
        ],
        max_tokens=16,
        temperature=1.2 # pick something more random to ensure uniqueness among titles
    )

    result = completion.choices[0].message.content.replace('"', '')
    return result

async def get_embedding(content: str) -> List[float]:
    response = await client.embeddings.create(
        input=content,
        model='text-embedding-ada-002'
    )
    return response.data[0].embedding

async def chat_completion(query: str, relevant_notes: List[str]) -> str:
    notes = '\n'.join(relevant_notes)

    response = await client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are a personal assistant helping a person remember what their ideas and thoughts were.'},
            {'role': 'system', 'content': f'Use this newline-separated list of notes to answer all questions: {notes}'},
            {'role': 'system', 'content': 'Respond in the style of the query, and succinctly summarize the important notes to answer the question.'},
            {'role': 'user', 'content': query}
        ]
    )
    return response.choices[0].message.content

