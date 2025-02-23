import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Mic, Send } from "lucide-react";
import { motion } from "framer-motion";
import {
  useChatInteract,
  useChatMessages,
  IStep,
} from "@chainlit/react-client";
import { useMemo, useRef, useState } from "react";

function flattenMessages(messages: IStep[], condition: (node: IStep) => boolean): IStep[] {
  return messages.reduce((acc: IStep[], node) => {
    if (condition(node)) acc.push(node);
    if (node.steps?.length) acc.push(...flattenMessages(node.steps, condition));
    return acc;
  }, []);
}

export function Playground() {
  const [inputValue, setInputValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const { sendMessage,sendAudioChunk, startAudioStream, endAudioStream } = useChatInteract();
  const { messages } = useChatMessages();

  const flatMessages = useMemo(() => flattenMessages(messages, (m) => m.type.includes("message")), [messages]);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    sendMessage({ name: "user", type: "user_message", output: inputValue }, []);
    setInputValue("");
  };

  // Audio-related refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const microphoneRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const startListening = async () => {
    try {
      if (isListening) {
        console.warn("Already listening...");
        return;
      }
  
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop(); // Stop any previous recording
      }
  
      startAudioStream(); // Start only if not already started
  
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      microphoneRef.current = audioContextRef.current.createMediaStreamSource(stream);
      microphoneRef.current.connect(analyserRef.current);
  
      setIsListening(true);
  
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: "audio/webm" });
  
      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          const arrayBuffer = await event.data.arrayBuffer();
          const audioData = new Int16Array(arrayBuffer.byteLength / 2);
          new DataView(arrayBuffer).getInt16(0, true);
          for (let i = 0; i < audioData.length; i++) {
            audioData[i] = new DataView(arrayBuffer).getInt16(i * 2, true);
          }
          sendAudioChunk(false, "audio/webm", Date.now(), audioData);
        }
      };
  
      mediaRecorderRef.current.onstart = () => {
        sendAudioChunk(true, "audio/webm", 0, new Int16Array());
      };
  
      mediaRecorderRef.current.onstop = () => {
        sendAudioChunk(false, "audio/webm", Date.now(), new Int16Array());
        endAudioStream(); // Ensure the stream is closed properly
      };
  
      mediaRecorderRef.current.start(500); // Send chunks every 500ms
    } catch (error) {
      console.error("Microphone access denied:", error);
    }
  };
  const stopListening = () => {
    if (!isListening) return;
  
    setIsListening(false);
    endAudioStream(); // Ensure we close the WebSocket stream properly
  
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
  
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    // Stop all media stream tracks
    if (microphoneRef.current) {
      microphoneRef.current.disconnect();
      microphoneRef.current.mediaStream.getTracks().forEach(track => track.stop());
    }
  };
  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
      <div className="max-w-2xl w-full space-y-4 flex flex-col flex-1 overflow-auto">
        {flatMessages.map((message) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex items-center space-x-3 bg-gray-800 p-3 rounded-lg"
          >
            <span className="text-pink-500">✦</span>
            <p className="flex-1 text-white">{message.output}</p>
          </motion.div>
        ))}
      </div>
      <div className="w-full max-w-2xl bg-gray-900 p-4 rounded-lg flex items-center space-x-2 mt-4">
        <Input
          className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-gray-500"
          placeholder="Type your message here..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyUp={(e) => e.key === "Enter" && handleSendMessage()}
        />
        <Button onClick={handleSendMessage} className="bg-pink-500 hover:bg-pink-600 text-white">
          <Send size={18} />
        </Button>
        <Button
          onClick={() =>  isListening ? stopListening() : startListening()}
          className={`p-2 rounded-full ${isListening ? "bg-green-500" : "bg-gray-700"}`}
        >
          <Mic size={20} className="text-white" />
        </Button>
      </div>
    </div>
  );
}
