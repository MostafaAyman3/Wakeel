"use client";

import React, { useState, useRef } from "react";
import { getAuthToken } from "@/lib/auth";

// Use absolute URL to bypass Next.js proxy which sometimes drops multipart/form-data requests (ECONNRESET)
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
      setError("Please allow microphone access to use the voice assistant.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      // Stop all tracks to release mic
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
    formData.append("history", JSON.stringify(history.slice(-6))); // Keep last 3 turns

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
        throw new Error(`Server returned ${response.status}`);
      }

      // Read headers for text
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

      // Play audio response
      const audioBlobResponse = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlobResponse);
      const audio = new Audio(audioUrl);
      audio.play();

    } catch (err) {
      console.error("Error sending voice request", err);
      setError("Failed to process voice command.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
        المساعد الصوتي (Voice Assistant)
      </h2>
      
      <div className="flex flex-col items-center">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
          className={`relative p-6 rounded-full transition-all duration-300 shadow-md flex items-center justify-center
            ${
              isRecording
                ? "bg-red-100 text-red-600 animate-pulse border-2 border-red-500"
                : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg hover:-translate-y-1"
            }
            ${isProcessing ? "opacity-50 cursor-not-allowed" : ""}
          `}
          style={{ width: "80px", height: "80px" }}
        >
          {isProcessing ? (
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
          ) : (
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          )}
        </button>

        <p className="mt-4 text-sm font-medium text-gray-600 dark:text-gray-300">
          {isRecording ? "جاري التسجيل... (اضغط للإيقاف)" : isProcessing ? "جاري المعالجة..." : "اضغط للتحدث مع الوكيل"}
        </p>

        {error && <p className="mt-2 text-sm text-red-500">{error}</p>}

        {(userText || replyText) && (
          <div className="mt-6 w-full space-y-4 text-right">
            {userText && (
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">إنت قولت:</span>
                <p className="text-gray-800 dark:text-gray-200">{userText}</p>
              </div>
            )}
            
            {replyText && (
              <div className="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg border border-blue-100 dark:border-blue-800">
                <span className="text-xs text-blue-500 dark:text-blue-400 block mb-1">الوكيل بيرد:</span>
                <p className="text-blue-800 dark:text-blue-200 font-medium">{replyText}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
