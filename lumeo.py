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
from pymongo import MongoClient
from datetime import datetime

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

# Connect to MongoDB
MONGO_URI = "mongodb://lumen_admin:kush@127.0.0.1:27017/lumeo_db?authSource=lumeo_db"
client = MongoClient(MONGO_URI)
db = client["lumeo_db"]  # Database name
transcripts_collection = db["transcripts"]  # Collection name

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
        if message_type == "ConversationStarted":
            cl.user_session.set("audio_start_time", time.time())
            
        elif message_type == "AddTranscript":
            transcript = msg.get("metadata", {}).get("transcript", "").strip()
            if transcript:
                buffer = cl.user_session.get("transcript_buffer", [])
                buffer.append(transcript)
                cl.user_session.set("transcript_buffer", buffer)
                cl.user_session.set("last_buffer_update", time.time())
                
                # Check if transcript ends with sentence terminator
                if transcript[-1] in ('.', '?', '!'):
                    await flush_transcript_buffer()

        elif message_type == "ResponseCompleted":
            if content := msg.get("content", ""):
                await cl.Message(
                    author="Lumeo",
                    content=content
                ).send()

        elif message_type == "ResponseInterrupted":
            if content := msg.get("content", ""):
                if stream := cl.user_session.get("transcript_stream"):
                    await stream.update()
                    if cl.user_session.get("transcript_stream"):
                        cl.user_session.delete("transcript_stream")
                
                await cl.Message(
                    author="Lumeo",
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
        
        tool_tuple = next((tool for tool in tools if tool[0]["name"] == tool_name), None)
        
        if tool_tuple:
            tool_func = tool_tuple[1]
            
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_params)  # ✅ Correct: Await async functions
            else:
                result = tool_func(**tool_params)           
            time.sleep(0.1)
            
            # Log tool usage
            session_id = cl.user_session.get("id", "unknown_session")
            try:
                transcripts_collection.insert_one({
                    "timestamp": datetime.now().isoformat(),
                    "content": f"Tool usage: {tool_name}",
                    "session_id": session_id
                })
                logger.info(f"💾 Saved tool usage: {tool_name}")
            except Exception as e:
                logger.error(f"❌ Failed to save tool usage: {str(e)}")
            
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
                cl.run_sync(
                    client.websocket.send(json.dumps(response_message))
                )
            
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
    client.add_event_handler(ServerMessageType.ResponseCompleted, message_handler)
    client.add_event_handler(ServerMessageType.ToolInvoke, tool_handler)

    return client



def init_db():
    """Initialize MongoDB (No need for explicit table creation in MongoDB)"""
    print("MongoDB initialized successfully")

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
    
    asyncio.create_task(audio_playback())
    asyncio.create_task(buffer_monitor())
    
    await cl.Message(content = "👋🏽 Hi there, Press 'P' to start or stop talking with me",
                     author = "Lumeo").send()

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
            template_id="flow-service-assistant-humphrey",
            template_variables={
                "persona": "Your name is Lumeo, a voice-interactive AI assistant",
                "style": "Be Friendly and Helpful. You are a helpful assistant that can help with a variety of tasks.",
                "context": "Provide concise answers using available tools"
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
    """Save buffered transcripts as a single entry in MongoDB"""
    buffer = cl.user_session.get("transcript_buffer", [])
    if buffer:
        full_transcript = " ".join(buffer)
        session_id = cl.user_session.get("id", "unknown_session")

        try:
            # Update the document by appending the transcript to an array
            transcripts_collection.update_one(
                {"session_id": session_id},  
                {"$push": {"content": full_transcript}, "$set": {"timestamp": datetime.now().isoformat()}},  
                upsert=True  # Creates a new document if none exists
            )

            logger.info(f"💾 Updated transcript for session {session_id}: {full_transcript[:50]}...")
        except Exception as e:
            logger.error(f"❌ Failed to save transcript: {str(e)}")

        cl.user_session.set("transcript_buffer", [])



async def buffer_monitor():
    while True:
        last_update = cl.user_session.get("last_buffer_update", 0)
        if time.time() - last_update > 2.0:  # 2 second timeout
            await flush_transcript_buffer()
        await asyncio.sleep(0.5)