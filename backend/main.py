from fastapi import FastAPI
from .routers import stego_image, stego_audio, contact

app = FastAPI(title="ShadowCryption API")
app.include_router(stego_image.router)
app.include_router(stego_audio.router)
app.include_router(contact.router)
