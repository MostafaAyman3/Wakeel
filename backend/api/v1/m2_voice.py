"""
POST /api/v1/m2/voice

Receives audio blob from the frontend, converts it to text using Whisper,
triggers the M2 analysis loop, summarizes the results into a spoken response,
and returns the synthesized audio via ElevenLabs.
"""

from fastapi import APIRouter, UploadFile, File, Form, Request, Response
from typing import Optional

from backend.services.speech_service import speech_service
from backend.api.v1.m2_analyze import analyze_inventory
from backend.schemas.m2_analyze import AnalyzeRequest
from agents.shared.llm_client import llm_fast
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/m2", tags=["M2 Voice"])


@router.post("/voice")
async def process_voice_command(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("ar-EG")
) -> Response:
    """
    1. STT: audio -> text
    2. Analyze: Trigger inventory analysis
    3. LLM: Summarize analysis results based on user text
    4. TTS: summary -> audio response
    """
    try:
        audio_bytes = await audio.read()
        filename = audio.filename or "audio.webm"
        
        # 1. STT
        logger.info("Processing voice command STT", filename=filename)
        user_text = await speech_service.speech_to_text(audio_bytes, filename=filename)
        logger.info("Voice command recognized", user_text=user_text)
        
        if not user_text:
            user_text = "لم يتم التقاط أي صوت."
            
        # Parse history
        import json
        try:
            chat_history = json.loads(history)
        except:
            chat_history = []
        
        # 2. Trigger M2 Analyze
        logger.info("Triggering inventory analysis from voice command")
        analyze_req = AnalyzeRequest(trigger_source="manual", language=language)
        analyze_resp = await analyze_inventory(request, analyze_req)
        
        # 3. Summarize results with history
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        
        messages = []
        system_prompt = f"""
You are the M2 Inventory Voice Assistant (AERIE).
You are talking to the inventory manager.

Current Inventory Scan Results:
{json.dumps(analyze_resp.model_dump(), ensure_ascii=False)}

Instructions:
- Use the provided inventory scan results to answer the manager accurately. Mention specific product IDs/details if relevant.
- Do NOT just say "I found X alerts". Detail what the alerts are (e.g. shortage, expiry) if asked.
- Keep your answers brief, natural, and conversational.
- Since this will be converted to Text-to-Speech, DO NOT use markdown, asterisks, or bullet points.
- If the language is 'ar-EG', use natural Egyptian Arabic dialect. If 'en', use conversational English.
"""
        messages.append(SystemMessage(content=system_prompt.strip()))
        
        # Add history
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "agent":
                messages.append(AIMessage(content=msg.get("content", "")))
                
        # Add current user message
        messages.append(HumanMessage(content=user_text))

        reply_msg = await llm_fast.ainvoke(messages)
        reply_text = reply_msg.content.strip()
        logger.info("Generated voice response text", reply_text=reply_text)
        
        # 4. TTS
        logger.info("Processing voice response TTS")
        reply_audio = await speech_service.text_to_speech(reply_text)
        
        import urllib.parse
        encoded_text = urllib.parse.quote(reply_text)
        encoded_user = urllib.parse.quote(user_text)
        
        return Response(
            content=reply_audio, 
            media_type="audio/mpeg",
            headers={
                "X-Recognized-Text": encoded_user,
                "X-Reply-Text": encoded_text
            }
        )
    except Exception as e:
        logger.error("Error in /voice endpoint", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
