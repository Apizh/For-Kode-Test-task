from fastapi import FastAPI, HTTPException, Header
from os.path import exists as os_path_exists
from pydantic import BaseModel
from base64 import b64decode
from typing import List, Optional
import json
import aiohttp

app = FastAPI()

# Предустановленные пользователи  "Basic dXNlcjE6cGFzc3dvcmQx"
USER_CREDENTIALS = {
    "user1": "password1",
    "user2": "password2"
}

# Файл для хранения заметок
NOTES_FILE = 'notes.json'


# Вспомогательная функция для проверки аутентификации
def authenticate(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Basic '):
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Decode the base64 encoded credentials
    try:
        credentials = b64decode(authorization[len('Basic '):]).decode('utf-8')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials format")

    #Split the credentials into username and password
    try:
        username, password = credentials.split(':', 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials format")

    # Check if the provided credentials are correct
    if USER_CREDENTIALS.get(username) != password:
        raise HTTPException(status_code=403, detail="Forbidden")


# Вспомогательная функция для загрузки заметок
def load_notes():
    if not os_path_exists(NOTES_FILE):
        return {}
    with open(NOTES_FILE, 'r') as file:
        return json.load(file)


# Вспомогательная функция для сохранения заметок
def save_notes(notes):
    with open(NOTES_FILE, 'w') as file:
        json.dump(notes, file)


# Модель данных для заметок
class NoteIn(BaseModel):
    title: str
    content: str


class NoteOut(BaseModel):
    id: int
    title: str
    content: str


# Функция для проверки орфографии с использованием Яндекс.Спеллер
async def check_spelling(text: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
                'https://speller.yandex.net/services/spellservice.json/checkText',
                data={'text': text}
        ) as response:
            result = await response.json()
            return result


@app.post("/notes/", response_model=NoteOut)
async def add_note(note: NoteIn, authorization: Optional[str] = Header(None)):
    authenticate(authorization)

    notes = load_notes()
    note_id = len(notes) + 1
    spelling_result = await check_spelling(note.content)

    if spelling_result:
        raise HTTPException(status_code=400, detail="Spelling errors found")

    notes[note_id] = {"title": note.title, "content": note.content}
    save_notes(notes)
    return {**note.dict(), "id": note_id}


@app.get("/notes/", response_model=List[NoteOut])
def get_notes(authorization: Optional[str] = Header(None)):
    authenticate(authorization)

    notes = load_notes()
    return [{"id": note_id, **note} for note_id, note in notes.items()]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
