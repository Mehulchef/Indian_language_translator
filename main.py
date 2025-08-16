# FastAPI Voice Translation Backend
# Install requirements: pip install fastapi uvicorn SpeechRecognition googletrans==4.0.0-rc1 gTTS playsound==1.2.2 pyaudio

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
from langdetect import detect
import pygame
import io
import tempfile
import os
import base64
from typing import Optional
import json

app = FastAPI(title="Voice Translation API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 22 official Indian languages with Google Translate codes
indian_languages = {
    'Assamese': 'as',
    'Bengali': 'bn',
    'Bodo': 'brx',
    'Dogri': 'doi',
    'Gujarati': 'gu',
    'Hindi': 'hi',
    'Kannada': 'kn',
    'Kashmiri': 'ks',
    'Konkani': 'kok',
    'Maithili': 'mai',
    'Malayalam': 'ml',
    'Manipuri': 'mni',
    'Marathi': 'mr',
    'Nepali': 'ne',
    'Odia': 'or',
    'Punjabi': 'pa',
    'Sanskrit': 'sa',
    'Santali': 'sat',
    'Sindhi': 'sd',
    'Tamil': 'ta',
    'Telugu': 'te',
    'Urdu': 'ur'
}

# Initialize translator and pygame for audio playback
translator = Translator()
pygame.mixer.init()

# Pydantic models for request/response
class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

class TranslationResponse(BaseModel):
    translated_text: str
    original_text: str
    source_lang: str
    target_lang: str
    status: str

class TTSRequest(BaseModel):
    text: str
    target_lang: str

class TTSResponse(BaseModel):
    audio_data: str
    target_lang: str
    status: str

class SpeechRecognitionResponse(BaseModel):
    recognized_text: str
    source_lang: str
    detected_lang: Optional[str]
    status: str

@app.get("/")
async def root():
    return {
        "message": "Voice Translation FastAPI Backend",
        "status": "running",
        "endpoints": {
            "translate": "/api/translate",
            "speech_to_text": "/api/speech-to-text", 
            "text_to_speech": "/api/text-to-speech",
            "languages": "/api/languages",
            "health": "/health"
        }
    }

@app.post("/api/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Translate text using Google Translate
    This endpoint connects to your React frontend's useTranslation hook
    """
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Use googletrans for translation (your original Python logic)
        translated = translator.translate(
            text, 
            src=request.source_lang, 
            dest=request.target_lang
        )
        
        return TranslationResponse(
            translated_text=translated.text,
            original_text=text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Translation failed: {str(e)}"
        )

@app.post("/api/speech-to-text", response_model=SpeechRecognitionResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    source_lang: str = Form(...)
):
    """
    Convert speech to text using SpeechRecognition library
    This endpoint handles audio upload from your React frontend
    """
    try:
        # Save uploaded audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            content = await audio.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        # Use SpeechRecognition (your original Python logic)
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = recognizer.record(source)
        
        # Recognize speech with language specification
        text = recognizer.recognize_google(
            audio_data, 
            language=f"{source_lang}-IN"
        )
        
        # Auto-detect language if needed
        detected_lang = detect(text) if text else None
        
        # Cleanup
        os.unlink(temp_audio_path)
        
        return SpeechRecognitionResponse(
            recognized_text=text,
            source_lang=source_lang,
            detected_lang=detected_lang,
            status="success"
        )
        
    except sr.UnknownValueError:
        raise HTTPException(
            status_code=400, 
            detail="Could not understand the speech"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Speech recognition failed: {str(e)}"
        )

@app.post("/api/text-to-speech", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using gTTS (Google Text-to-Speech)
    This endpoint provides audio for your React frontend's audio playback
    """
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Use gTTS to generate speech (your original Python logic)
        tts = gTTS(text=text, lang=request.target_lang, slow=False)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
            tts.save(temp_audio_path)
        
        # Read file and encode as base64 for frontend
        with open(temp_audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Cleanup
        os.unlink(temp_audio_path)
        
        return TTSResponse(
            audio_data=audio_base64,
            target_lang=request.target_lang,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Text-to-speech failed: {str(e)}"
        )

@app.get("/api/languages")
async def get_languages():
    """
    Get available Indian languages
    This endpoint provides language options for your React frontend
    """
    return {
        "languages": indian_languages,
        "status": "success"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "FastAPI Voice Translation service is running",
        "message": "All systems operational"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI Voice Translation Backend...")
    print("📋 Available endpoints:")
    print("   POST /api/translate - Translate text")
    print("   POST /api/speech-to-text - Convert speech to text") 
    print("   POST /api/text-to-speech - Convert text to speech")
    print("   GET /api/languages - Get available languages")
    print("   GET /health - Health check")
    print("\n🔗 Your React frontend should call: http://localhost:8000")
    print("\n📦 Required packages:")
    print("   pip install fastapi uvicorn SpeechRecognition googletrans==4.0.0-rc1 gTTS playsound==1.2.2 pyaudio pygame")
    print("\n🏃‍♂️ To run:")
    print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)