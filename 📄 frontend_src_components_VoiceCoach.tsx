"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, Brain, Loader2 } from "lucide-react";

interface SkillSignal {
  skill: string;
  confidence: "high" | "medium" | "low";
}

interface TranscriptEntry {
  speaker: "learner" | "coach";
  text: string;
  timestamp: Date;
  tone?: string;
}

interface VoiceCoachProps {
  userId: string;
  onSessionComplete: (profile: Record<string, unknown>) => void;
}

export default function VoiceCoach({ userId, onSessionComplete }: VoiceCoachProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isCoachSpeaking, setIsCoachSpeaking] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [detectedSkills, setDetectedSkills] = useState<SkillSignal[]>([]);
  const [currentTone, setCurrentTone] = useState<string>("neutral");
  const [sessionDuration, setSessionDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const sessionIdRef = useRef<string>(`session_${userId}_${Date.now()}`);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // Session timer
  useEffect(() => {
    if (isConnected) {
      timerRef.current = setInterval(() => {
        setSessionDuration((d) => d + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isConnected]);

  const connectToCoach = useCallback(async () => {
    try {
      // Initialize audio context for playback
      audioContextRef.current = new AudioContext({ sampleRate: 24000 });

      // Connect WebSocket to Nova 2 Sonic backend
      const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/coaching/${sessionIdRef.current}?user_id=${userId}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        startMicrophoneCapture();
      };

      wsRef.current.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          // Binary audio from coach (Nova 2 Sonic output)
          await playCoachAudio(event.data);
        } else {
          // JSON control/event message
          const message = JSON.parse(event.data);
          handleServerEvent(message);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setIsRecording(false);
        stopMicrophoneCapture();
      };

      wsRef.current.onerror = (err) => {
        setError("Connection error. Please check your network and try again.");
        console.error("WebSocket error:", err);
      };

    } catch (err) {
      setError("Failed to initialize voice session. Please allow microphone access.");
      console.error("Connection failed:", err);
    }
  }, [userId]);

  const handleServerEvent = (message: Record<string, unknown>) => {
    switch (message.type) {
      case "session.started":
        console.log("Coaching session started:", message.session_id);
        break;

      case "transcript.learner":
        if (message.text && (message.text as string).trim()) {
          setTranscript((prev) => {
            // Update last learner entry if not final, otherwise add new
            const last = prev[prev.length - 1];
            if (last?.speaker === "learner" && !message.is_final) {
              return [
                ...prev.slice(0, -1),
                { ...last, text: last.text + (message.text as string) },
              ];
            }
            return [
              ...prev,
              {
                speaker: "learner",
                text: message.text as string,
                timestamp: new Date(),
              },
            ];
          });
        }
        break;

      case "transcript.coach":
        setIsCoachSpeaking(true);
        setTranscript((prev) => [
          ...prev,
          {
            speaker: "coach",
            text: message.text as string,
            timestamp: new Date(),
            tone: currentTone,
          },
        ]);
        setTimeout(() => setIsCoachSpeaking(false), 3000);
        break;

      case "analysis.tone":
        setCurrentTone(message.tone as string);
        break;

      case "analysis.skill_detected":
        setDetectedSkills((prev) => {
          const exists = prev.find((s) => s.skill === message.skill);
          if (exists) return prev;
          return [
            ...prev,
            {
              skill: message.skill as string,
              confidence: message.confidence as "high" | "medium" | "low",
            },
          ];
        });
        break;

      case "session.summary":
        onSessionComplete(message.profile as Record<string, unknown>);
        break;

      case "error":
        setError(message.message as string);
        break;
    }
  };

  const startMicrophoneCapture = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    mediaRecorderRef.current = new MediaRecorder(stream, {
      mimeType: "audio/webm;codecs=pcm",
    });

    mediaRecorderRef.current.ondataavailable = (event) => {
      if (
        event.data.size > 0 &&
        wsRef.current?.readyState === WebSocket.OPEN
      ) {
        wsRef.current.send(event.data);
      }
    };

    mediaRecorderRef.current.start(500); // Send 500ms chunks
    setIsRecording(true);
  };

  const stopMicrophoneCapture = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const playCoachAudio = async (audioBlob: Blob) => {
    if (!audioContextRef.current) return;

    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);

    const source = audioContextRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContextRef.current.destination);
    source.start();
  };

  const endSession = () => {
    wsRef.current?.send(JSON