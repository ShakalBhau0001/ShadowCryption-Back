from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import tempfile, os, io

from ..core.crypto import fernet_from_password, encrypt_and_make_payload
from ..core.audio_stego import embed_payload_in_wav_file, extract_payload_from_wav_file
from ..core.constants import AUDIO_MAGIC, HEADER_SIZE

router = APIRouter(prefix="/api", tags=["audio"])


def save_upload_file_tmp(upload: UploadFile, max_bytes: int = 30 * 1024 * 1024) -> str:
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(upload.filename)[1] or ""
    )
    total = 0
    while True:
        chunk = upload.file.read(1024 * 64)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            tmp.close()
            os.unlink(tmp.name)
            raise HTTPException(status_code=413, detail="Uploaded file too large")
        tmp.write(chunk)
    tmp.flush()
    tmp.close()
    return tmp.name


@router.post("/encode/audio")
def encode_audio(
    audio: UploadFile = File(...), password: str = Form(...), text: str = Form(...)
):
    if not text or not password:
        raise HTTPException(status_code=400, detail="`text` and `password` required")
    if audio.content_type and not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid audio upload")

    inp = save_upload_file_tmp(audio)
    out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out_tmp.close()
    try:
        payload = encrypt_and_make_payload(text.encode("utf-8"), password, AUDIO_MAGIC)
        embed_payload_in_wav_file(inp, payload, out_tmp.name)
        return StreamingResponse(
            open(out_tmp.name, "rb"),
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="stego.wav"'},
        )
    finally:
        try:
            os.unlink(inp)
        except:
            pass
        try:
            os.unlink(out_tmp.name)
        except:
            pass


@router.post("/decode/audio")
def decode_audio(audio: UploadFile = File(...), password: str = Form(...)):
    if not password:
        raise HTTPException(status_code=400, detail="`password` required")

    inp = save_upload_file_tmp(audio)
    try:
        header = extract_payload_from_wav_file(inp, HEADER_SIZE)
        if header[:4] != AUDIO_MAGIC:
            raise HTTPException(status_code=400, detail="No audio payload")
        salt = header[4:20]
        enc_len = int.from_bytes(header[20:24], "big")
        full_payload = extract_payload_from_wav_file(inp, HEADER_SIZE + enc_len)
        _, encrypted_bytes = (
            full_payload[24 : 24 + enc_len],
            full_payload[24 : 24 + enc_len],
        )
        fernet = fernet_from_password(password, salt)
        try:
            decrypted = fernet.decrypt(encrypted_bytes)
        except:
            raise HTTPException(status_code=400, detail="Decryption failed")
        return StreamingResponse(
            io.BytesIO(decrypted),
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="decrypted.txt"'},
        )
    finally:
        try:
            os.unlink(inp)
        except:
            pass
