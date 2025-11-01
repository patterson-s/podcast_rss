from __future__ import annotations
import whisper
import tempfile
import os
from pathlib import Path
from typing import Optional

class Transcriber:
    def __init__(self, model_name: str = "medium"):
        self.model_name = model_name
        self.model = None
    
    def load_model(self):
        if self.model is None:
            self.model = whisper.load_model(self.model_name)
    
    def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str) -> Optional[str]:
        self.load_model()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            result = self.model.transcribe(tmp_path)
            return result["text"].strip()
        except Exception as e:
            return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
