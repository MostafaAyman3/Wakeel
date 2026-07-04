"use client";

import React, { useState, useRef } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";
import { getAuthToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export default function VoiceAssistantPanel() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [userText, setUserText] = useState("");
  const [replyText, setReplyText] = useState("");
  const [error, setError] = useState("");
  const [history, setHistory] = useState<{role: string, content: string}[]>([]);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = handleStop;
      mediaRecorder.start();
      setIsRecording(true);
      setError("");
      setUserText("");
      setReplyText("");
    } catch (err) {
      console.error("Error accessing microphone", err);
      setError("يرجى السماح بالوصول للميكروفون لاستخدام المساعد الصوتي.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      setIsRecording(false);
    }
  };

  const handleStop = async () => {
    setIsProcessing(true);
    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    formData.append("language", "ar-EG");
    formData.append("history", JSON.stringify(history.slice(-6)));

    try {
      const token = await getAuthToken();
      const response = await fetch(`${API_BASE}/api/v1/m2/voice`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(detail || `Server returned ${response.status}`);
      }

      const recognized = response.headers.get("X-Recognized-Text");
      const reply = response.headers.get("X-Reply-Text");
      
      let recText = "";
      let repText = "";
      
      if (recognized) {
        recText = decodeURIComponent(recognized);
        setUserText(recText);
      }
      if (reply) {
        repText = decodeURIComponent(reply);
        setReplyText(repText);
      }

      if (recText && repText) {
        setHistory(prev => [
          ...prev, 
          { role: "user", content: recText },
          { role: "agent", content: repText }
        ]);
      }

      const audioBlobResponse = await response.blob();
      if (audioBlobResponse.size > 0) {
        const audioUrl = URL.createObjectURL(audioBlobResponse);
        const audio = new Audio(audioUrl);
        audio.play().catch(() => {
          // Browser may block autoplay — that's OK
        });
      }

    } catch (err) {
      console.error("Error sending voice request", err);
      const msg = err instanceof Error ? err.message : "حدث خطأ أثناء معالجة الأمر الصوتي.";
      setError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate bg-surface p-6">
      <h2 className="mb-4 font-cairo text-lg font-semibold text-ivory">
        🎙️ المساعد الصوتي
        <span className="ms-2 rounded-full bg-gold/10 px-2 py-0.5 font-inter text-[10px] font-medium text-gold">
          Optional
        </span>
      </h2>
      
      <div className="flex flex-col items-center">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
          className={`relative flex h-20 w-20 items-center justify-center rounded-full transition-all duration-300 shadow-md
            ${
              isRecording
                ? "bg-danger/20 text-danger animate-pulse border-2 border-danger"
                : "bg-gold/10 text-gold border border-gold/30 hover:bg-gold/20 hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]"
            }
            ${isProcessing ? "opacity-50 cursor-not-allowed" : ""}
          `}
        >
          {isProcessing ? (
            <Loader2 className="h-8 w-8 animate-spin" />
          ) : isRecording ? (
            <MicOff className="h-8 w-8" />
          ) : (
            <Mic className="h-8 w-8" />
          )}
        </button>

        <p className="mt-3 text-sm font-medium text-sage">
          {isRecording ? "جاري التسجيل... اضغط للإيقاف" : isProcessing ? "جاري المعالجة..." : "اضغط للتحدث مع الوكيل"}
        </p>

        {error && (
          <p className="mt-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        {(userText || replyText) && (
          <div className="mt-5 w-full space-y-3" dir="rtl">
            {userText && (
              <div className="rounded-lg bg-midnight p-4 border border-slate">
                <span className="mb-1 block text-xs text-sage">إنت قولت:</span>
                <p className="text-ivory">{userText}</p>
              </div>
            )}
            
            {replyText && (
              <div className="rounded-lg border border-gold/20 bg-gold/5 p-4">
                <span className="mb-1 block text-xs text-gold/60">الوكيل بيرد:</span>
                <p className="font-medium text-ivory">{replyText}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
