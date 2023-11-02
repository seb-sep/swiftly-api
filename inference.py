import openai
import os
import io
from typing import List

# setup opnenai api key
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key == None:
    print("No OpenAI key env var found.")
    exit()



def transcribe_audio(audio_bytes: io.BytesIO) -> str:
    '''Transcribe the given audio file to text.'''

    transcript = openai.Audio.transcribe('whisper-1', audio_bytes)
    return transcript['text']

def generate_note_title(note: str) -> str:
    '''Generate a title for a note.'''

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Write a brief, unique title summarizing the following note in about four words."},
            {"role": "user", "content": note}
        ],
        max_tokens=16,
        temperature=1.5 # pick something more random to ensure uniqueness among titles
    )

    return completion.choices[0].message.content

def get_embedding(content: str):
    response = openai.Embedding.create(
        input=content,
        model='text-embedding-ada-002'
    )
    return response['data'][0]['embedding']

async def chat_completion(query: str, relevant_notes: List[str]) -> str:
    notes = '\n'.join(relevant_notes)

    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are a personal assistant helping a person remember what their ideas and thoughts were.'},
            {'role': 'system', 'content': f'Use this newline-separated list of notes to answer all questions: {notes}'},
            {'role': 'system', 'content': 'Respond in the style of the query, and succinctly summarize the important notes to answer the question.'},
            {'role': 'user', 'content': query}
        ]
    )
    return response['choices'][0]['message']['content']

