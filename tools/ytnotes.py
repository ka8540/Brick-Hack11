"""YouTube notes generation tool."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import os
from typing import Optional, Dict, Any, List
import logging
import re
from urllib.parse import urlparse, parse_qs
from openai import AsyncOpenAI
from dotenv import load_dotenv
import chainlit as cl

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
generate_youtube_notes_def = {
    "name": "generate_youtube_notes",
    "description": "Generates structured notes from YouTube videos. Auto-triggers when user mentions: notes, summary, key points, or video analysis. Always uses stored YouTube URL.",
    "parameters": {
        "type": "object",
        "properties": {
            "youtube_url": {
                "type": "string",
                "description": "YouTube URL from chat settings."
            }
        },
        "required": []  
    }
}

def extract_video_id(youtube_url: str) -> Optional[str]:
    """Extract video ID from various forms of YouTube URLs."""
    try:
        if "youtu.be" in youtube_url:
            return youtube_url.split("/")[-1].split("?")[0]
        
        parsed_url = urlparse(youtube_url)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query)['v'][0]
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
            elif parsed_url.path.startswith('/v/'):
                return parsed_url.path.split('/')[2]
    except Exception as e:
        logger.error(f"Error extracting video ID: {str(e)}")
    return None

class YouTubeProcessor:
    def __init__(self):
        self.output_dir = "captions"
        os.makedirs(self.output_dir, exist_ok=True)

    async def process_video(self, video_id: str) -> Optional[dict]:
        """
        Process a YouTube video by fetching its captions and generating AI notes.
        Returns a dictionary containing the processed content.
        """
        try:
            logger.info(f"🎥 Processing YouTube video: {video_id}")
            transcript = await self._fetch_transcript(video_id)
            
            if not transcript:
                return None
            formatted_content = []
            raw_text = ""
            for item in transcript:
                minutes = int(item['start'] // 60)
                seconds = int(item['start'] % 60)
                timestamp = f"{minutes:02d}:{seconds:02d}"
                text = item['text'].strip()
                formatted_content.append({
                    'timestamp': timestamp,
                    'text': text,
                    'duration': item['duration']
                })
                raw_text += f"{text} "

            ai_notes = await self._generate_ai_notes(raw_text)
            
            # Save notes to file
            output_file = os.path.join(self.output_dir, f"{video_id}_notes.md")
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(ai_notes['formatted_notes'])
            
            logger.info(f"✅ Successfully processed video {video_id}")
            logger.info(f"📝 Notes saved to: {output_file}")
            
            return {
                'content': formatted_content,
                'ai_notes': ai_notes,
                'video_id': video_id,
                'source_type': 'youtube',
                'file_path': output_file
            }

        except Exception as e:
            logger.error(f"❌ Error processing video {video_id}: {str(e)}")
            return None

    async def _generate_ai_notes(self, transcript_text: str) -> Dict[str, Any]:
        """Generate structured notes using AI."""
        try:
            logger.info("🤖 Generating AI notes...")
            
            prompt = f"""
            Please analyze this video transcript and create well-structured notes with the following sections:
            1. Summary (2-3 sentences)
            2. Main Topics (bullet points of key topics covered)
            3. Key Points (detailed bullet points of important information)
            4. Action Items (if any takeaways or actions mentioned)
            
            Transcript:
            {transcript_text}
            """
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert note-taker who creates clear, concise, and well-structured notes from video transcripts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            notes = response.choices[0].message.content
            
            formatted_notes = f"""# Video Notes

{notes}

---
*Notes generated by AI from video transcript*
"""
            
            return {
                'raw_notes': notes,
                'formatted_notes': formatted_notes
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating AI notes: {str(e)}")
            return {
                'raw_notes': f'Error: {str(e)}',
                'formatted_notes': '# Error\nFailed to generate AI notes. Please check:\n1. OpenAI API key is valid\n2. Transcript contains meaningful content'
            }

    async def _fetch_transcript(self, video_id: str):
        """Fetch transcript for a video, trying both manual and auto-generated captions."""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            try:
                logger.info("🔍 Searching for manual captions...")
                transcript = transcript_list.find_manually_created_transcript(['en']).fetch()
                logger.info("✅ Manual captions found!")
                return transcript
            except NoTranscriptFound:
                logger.info("⚠️ No manual captions found. Trying auto-generated captions...")
                transcript = transcript_list.find_generated_transcript(['en']).fetch()
                logger.info("✅ Auto-generated captions found!")
                return transcript
                
        except NoTranscriptFound:
            logger.error("❌ No captions available (manual or auto-generated)")
        except TranscriptsDisabled:
            logger.error("❌ Captions are disabled for this video")
        except Exception as e:
            logger.error(f"❌ Error fetching transcript: {str(e)}")
        
        return None

async def generate_youtube_notes_handler(youtube_url: str = None) -> Dict[str, Any]:
    """Handler for the generate_youtube_notes tool."""
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return {
                "error": "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
            }

        url = cl.user_session.get("youtube_url")
        
        if not url:
            return {
                "error": "No YouTube URL configured. Please set a URL in the chat settings first."
            }

        video_id = extract_video_id(url)
        if not video_id:
            return {
                "error": f"Invalid YouTube URL: {url}. Please check the URL in settings."
            }

        processor = YouTubeProcessor()
        result = await processor.process_video(video_id)

        if not result:
            return {
                "error": "Failed to generate notes. The video might not have captions available."
            }

        return {
            "success": True,
            "video_id": video_id,
            "notes": result['ai_notes']['formatted_notes'],
            "message": "✅ Successfully generated AI-processed notes from the video!",
            "file_path": result['file_path']
        }
    except Exception as e:
        logger.error(f"❌ Error generating YouTube notes: {str(e)}")
        return {"error": f"Failed to generate notes: {str(e)}"}

generate_youtube_notes = (generate_youtube_notes_def, generate_youtube_notes_handler) 