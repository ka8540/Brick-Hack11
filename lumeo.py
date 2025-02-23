import asyncio
import io
import ssl
import sys
import signal
import chainlit as cl
import pyaudio
from uuid import uuid4
import wave
import json
from tools import tools
from utils.common import logger
import time
import sqlite3
from datetime import datetime
from typing import Optional
import re
import jwt
from datetime import datetime, timedelta
import os
# Secret key for JWT
token_secret = os.getenv("TOKEN_SECRET", "supersecret")

def generate_token(username: str):
    """Generate a JWT token for authentication."""
    expiration = datetime.utcnow() + timedelta(hours=1)
    token = jwt.encode({
        "sub": username,
        "exp": expiration
    }, token_secret, algorithm="HS256")
    return token

from speechmatics_flow.client import WebsocketClient
from speechmatics_flow.models import (
    ConnectionSettings,
    Interaction,
    AudioSettings,
    ConversationConfig,
    ServerMessageType,
    ClientMessageType,
)
from speechmatics_flow.tool_function_param import ToolFunctionParam

import os
from dotenv import load_dotenv
from chainlit.input_widget import TextInput
load_dotenv()

CHUNK_SIZE = 1024
SEE_TRANSCRIPTS = True
AUTH_TOKEN = os.getenv("SPEECHMATICS_AUTH_TOKEN")
BUFFER_SIZE = 3200
SAMPLE_RATE = 16000
CHANNELS = 1

websocket_lock = asyncio.Lock()
audio_buffer = io.BytesIO()
p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,
    channels=CHANNELS,
    rate=SAMPLE_RATE,
    output=True
)

async def audio_playback():
    """Continuous audio playback from buffer"""
    while True:
        audio_to_play = audio_buffer.getvalue()
        if audio_to_play:
            try:
                stream.write(audio_to_play)
                audio_buffer.seek(0)
                audio_buffer.truncate(0)
            except Exception as e:
                logger.error(f"Playback error: {str(e)}")
        await asyncio.sleep(0.01)

async def message_handler(msg: dict):
    if isinstance(msg, dict):
        message_type = msg.get("message", "")
        if message_type == "AddTranscript":
            transcript = msg.get("metadata", {}).get("transcript", "").strip()
            if transcript:
                logger.info(f"🎤 Processing transcript: {transcript}")
                
                # YouTube notes handling
                if "generate notes" in transcript.lower():
                    url = cl.user_session.get("youtube_url")
                    
                    if not url:
                        await cl.Message(
                            content="Please provide a YouTube URL using the text input above first.",
                            author="Lumi"
                        ).send()
                        return
                    
                    if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', url):
                        await cl.Message(
                            content="❌ Invalid YouTube URL format. Please check the URL and try again.",
                            author="Lumi"
                        ).send()
                        return
                    
                    await cl.Message(content="🔍 Processing video...").send()
                    
                    from tools.ytnotes import generate_youtube_notes_handler
                    result = await generate_youtube_notes_handler(url)
                    
                    if "notes" in result:
                        await cl.Message(
                            content=f"📝 Here are your notes:\n\n{result['notes']}",
                            author="Lumi"
                        ).send()
                        return
                    elif "error" in result:
                        await cl.Message(
                            content=f"❌ Error: {result['error']}",
                            author="Lumi"
                        ).send()
                        return
                
                return

        elif message_type == "ResponseCompleted":
            if content := msg.get("content", ""):
                await cl.Message(
                    author="Lumi",
                    content=content
                ).send()

        elif message_type == "ResponseInterrupted":
            if content := msg.get("content", ""):
                if stream := cl.user_session.get("transcript_stream"):
                    await stream.update()
                    if cl.user_session.get("transcript_stream"):
                        cl.user_session.delete("transcript_stream")
                
                await cl.Message(
                    author="Lumi",
                    content=f"[Interrupted] {content}"
                ).send()

async def binary_msg_handler(msg: bytes):
    """Handle outgoing audio - write to buffer and send AudioReceived"""
    if isinstance(msg, (bytes, bytearray)):
        audio_buffer.write(msg)        
        client = cl.user_session.get("client")
        if client and client.websocket:
            await client.websocket.send(json.dumps({
                "message": "AudioReceived",
                "seq_no": cl.user_session.get("seq_no", 0),
                "buffering": 0.02
            }))
            cl.user_session.set("seq_no", cl.user_session.get("seq_no", 0) + 1)

async def tool_handler(msg: dict):
    """Handle tool invocations from Flow"""
    logger.info(f"Tool invocation received: {json.dumps(msg, indent=2)}")
    
    function_data = msg.get("function", {})
    tool_name = function_data.get("name")
    tool_params = function_data.get("arguments", {})
    
    try:
        logger.info(f"🛠️ Executing tool: {tool_name} with params: {tool_params}")
        
        # Added pre-execution announcements for specific tools
        if tool_name == "open_browser":
            await cl.Message(
                content=f"Opening website {tool_params.get('url', '')} in your browser..."
            ).send()
        elif tool_name == "generate_youtube_notes":
            await cl.Message(
                content=f"📝 Generating notes from YouTube video: {tool_params.get('youtube_url', '')}..."
            ).send()
        
        tool_tuple = next((tool for tool in tools if tool[0]["name"] == tool_name), None)
        
        if tool_tuple:
            tool_func = tool_tuple[1]            
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_params)
            else:
                result = tool_func(**tool_params)
                
            time.sleep(0.1)            
            session_id = cl.user_session.get("id", "unknown_session")
            try:
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("""
                    INSERT INTO transcripts 
                    (timestamp, content, tool_name, session_id, metadata) 
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(), 
                    f"Executed {tool_name} with params: {json.dumps(tool_params)}",
                    tool_name,
                    session_id,
                    json.dumps({"result": str(result)})
                ))
                conn.commit()
                conn.close()
                logger.info(f"💾 Saved tool usage: {tool_name}")
            except Exception as e:
                logger.error(f"❌ Failed to save tool usage: {str(e)}")
            if tool_name == "generate_youtube_notes" and isinstance(result, dict):
                if "error" in result:
                    await cl.Message(
                        content=f"❌ {result['error']}",
                        author="Lumi"
                    ).send()
                elif "notes" in result:
                    await cl.Message(
                        content=result["notes"],
                        author="Lumi"
                    ).send()                    
                    if "file_path" in result:
                        await cl.Message(
                            content=f"✅ Notes have been saved to: {result['file_path']}",
                            author="Lumi"
                        ).send()
            
            if isinstance(result, dict):
                response_content = json.dumps(result)
            else:
                response_content = str(result)
                
            response_message = {
                "message": ClientMessageType.ToolResult,
                "id": msg["id"],
                "status": "ok",
                "content": response_content
            }            
            client = cl.user_session.get("client")
            if client and client.websocket:
                await client.websocket.send(json.dumps(response_message))
            
            return result
            
    except Exception as e:
        error_msg = f"Error executing {tool_name}: {str(e)}"
        logger.error(f"❌ {error_msg}")        
        response_message = {
            "message": ClientMessageType.ToolResult,
            "id": msg["id"],
            "status": "failed",
            "content": error_msg
        }
        
        client = cl.user_session.get("client")
        if client and client.websocket:
            await client.websocket.send(json.dumps(response_message))
            
        return {"error": error_msg}

async def setup_client():
    """Configure Speechmatics client with tools"""
    tool_configs = [ToolFunctionParam(type="function", function=tool[0]) 
                   for tool in tools]
    
    client = WebsocketClient(
        ConnectionSettings(
            url="wss://flow.api.speechmatics.com/v1/flow",
            auth_token=AUTH_TOKEN,
        )
    )    
    client.add_event_handler(ServerMessageType.AddAudio, binary_msg_handler)
    client.add_event_handler(ServerMessageType.AddTranscript, message_handler)
    client.add_event_handler(ServerMessageType.ToolInvoke, tool_handler)

    return client

def init_db():
    """Initialize database and create tables"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()        
        c.execute('DROP TABLE IF EXISTS transcripts')
        c.execute('''CREATE TABLE IF NOT EXISTS transcripts
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     timestamp TEXT NOT NULL,
                     content TEXT NOT NULL,
                     tool_name TEXT,
                     session_id TEXT NOT NULL,
                     metadata TEXT)''')
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {str(e)}")

@cl.on_chat_start
async def start():
    """Initialize chat session"""
    init_db()
    cl.user_session.set("track_id", str(uuid4()))
    client = await setup_client()
    cl.user_session.set("client", client)
    cl.user_session.set("audio_chunks", asyncio.Queue())
    cl.user_session.set("transcript_buffer", [])
    cl.user_session.set("last_buffer_update", time.time())
    
    # Initialize YouTube URL storage
    cl.user_session.set("youtube_url", None)
    
    # Configure persistent text input
    settings = await cl.ChatSettings(
        [
            TextInput(
                id="youtube_url",
                label="YouTube Video URL",
                placeholder="Paste URL here",
                tooltip="Enter YouTube URL to generate notes",
            )
        ]
    ).send()
    
    # Store initial URL if provided
    if url := settings.get("youtube_url"):
        cl.user_session.set("youtube_url", url)
    
    asyncio.create_task(audio_playback())
    asyncio.create_task(buffer_monitor())
    
    await cl.Message(
        content="👋 Hello i'm here. Press `P` to talk!",
        author="Lumi"
    ).send()

async def audio_generator():
    """Async generator for audio chunks"""
    while True:
        chunk = await cl.user_session.get("audio_chunks").get()
        if chunk is None:
            break
        yield chunk

class AsyncGeneratorIO:
    def __init__(self, generator):
        self.generator = generator
        self.buffer = b''
        self.eof = False

    async def read(self, size=-1):
        while len(self.buffer) < size or size == -1:
            try:
                chunk = await self.generator.__anext__()
                if chunk is None:  
                    self.eof = True
                    break
                self.buffer += chunk
            except StopAsyncIteration:
                self.eof = True
                break
        
        if size == -1:
            result = self.buffer
            self.buffer = b''
            return result
        else:
            result = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return result

@cl.on_audio_start
async def on_audio_start():
    """Start Speechmatics session"""
    client = cl.user_session.get("client")
    if not client:
        return False
    audio_stream = AsyncGeneratorIO(audio_generator())
    asyncio.create_task(client.run(
        interactions=[Interaction(audio_stream)],  
        audio_settings=AudioSettings(
            encoding="pcm_s16le",
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE
        ),
        conversation_config=ConversationConfig(
            template_id="flow-service-assistant-amelia",
            template_variables={
                "persona": "Your name is Lumi, a voice-interactive AI assistant",
                "style": "Be direct and don't ask follow-up questions. Use available tools automatically.",
                "context": "You have access to YouTube URL from user input. When user says 'generate notes' or similar, automatically use generate_youtube_notes tool with the stored URL. Never ask for URLs - use the stored value."
            }
        ),
        tools=[ToolFunctionParam(type="function", function=tool[0]) 
              for tool in tools]
    ))
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming audio - send directly to Speechmatics only"""
    await cl.user_session.get("audio_chunks").put(chunk.data)

@cl.on_audio_end
async def on_audio_end():
    """Handles end of user audio input"""
    await cl.user_session.get("audio_chunks").put(None)

@cl.on_stop
async def on_stop():
    """Cleanup for speechmatics client, pyaudio instance and stream"""
    stream.close()
    p.terminate()
    client = cl.user_session.get("client")
    if client:
        await client.close()

async def flush_transcript_buffer():
    """Save buffered transcripts as a single entry"""
    buffer = cl.user_session.get("transcript_buffer", [])
    if buffer:
        full_transcript = " ".join(buffer)
        session_id = cl.user_session.get("id", "unknown_session")
        
        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("""
                INSERT INTO transcripts 
                (timestamp, content, session_id, metadata) 
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(), 
                full_transcript, 
                session_id,
                json.dumps({"source": "voice_transcript"})
            ))
            conn.commit()
            conn.close()
            logger.info(f"💾 Saved complete transcript: {full_transcript[:50]}...")
        except Exception as e:
            logger.error(f"❌ Failed to save transcript: {str(e)}")
        
        cl.user_session.set("transcript_buffer", [])

async def buffer_monitor():
    while True:
        last_update = cl.user_session.get("last_buffer_update", 0)
        if time.time() - last_update > 2.0:  # 2 second timeout
            await flush_transcript_buffer()
        await asyncio.sleep(0.5)

async def extract_youtube_url(transcript: str) -> Optional[str]:
    """Extract YouTube URL from transcript text using regex"""
    import re
    # Match various YouTube URL formats
    pattern = r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]{11})'
    match = re.search(pattern, transcript)
    return match.group(0) if match else None

# Add this new function to handle YouTube note generation
async def create_youtube_notes(url: str) -> Optional[str]:
    """Generate notes from YouTube URL using ytnotes tool"""
    try:
        logger.info(f"🎬 Starting note generation for URL: {url}")
        from tools.ytnotes import generate_youtube_notes_handler
        result = await generate_youtube_notes_handler(url)
        
        logger.info(f"📊 Note generation result: {result}")
        
        if "error" in result:
            error_msg = f"Error: {result['error']}"
            logger.error(f"❌ {error_msg}")
            return error_msg
        
        notes = result.get("notes", "No notes generated")
        logger.info(f"✅ Successfully generated notes")
        return notes
    except Exception as e:
        error_msg = f"Failed to generate notes: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return error_msg

@cl.on_settings_update
async def handle_settings_update(settings):
    """Handle updates to YouTube URL"""
    if youtube_url := settings.get("youtube_url"):
        # Improved URL validation
        if re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/.+', youtube_url):
            cl.user_session.set("youtube_url", youtube_url)
            await cl.Message(
                content=f"✅ YouTube URL saved: {youtube_url}",
                author="Lumi"
            ).send()
        else:
            await cl.Message(
                content="❌ Invalid YouTube URL format. Please check and try again.",
                author="Lumi"
            ).send()

def get_user_token(username: str):
    """Retrieve the stored token for a user."""
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute("SELECT token FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def store_user_token(username: str, token: str):
    """Store the generated token in the database."""
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute("UPDATE users SET token = ? WHERE username = ?", (token, username))
    conn.commit()
    conn.close()

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    # if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"})
    # else:
        # return None
