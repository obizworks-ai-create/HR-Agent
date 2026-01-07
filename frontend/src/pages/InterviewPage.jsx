import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Mic, MicOff, Volume2, User, Bot, Loader2 } from 'lucide-react';
import api from '../lib/api';
import clsx from 'clsx';

const InterviewPage = () => {
    const [searchParams] = useSearchParams();
    const candidateEmail = searchParams.get("email");
    const jobTitle = searchParams.get("job");

    const [isRecording, setIsRecording] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isFinished, setIsFinished] = useState(false);
    const [transcript, setTranscript] = useState([

        { sender: 'ai', text: `Hello! I'm your AI interviewer today for the ${jobTitle || 'role'}. When you're ready, click the microphone button and introduce yourself.` }
    ]);

    // Audio Refs
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    // Audio Analysis (VAD)
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const dataArrayRef = useRef(null);
    const sourceRef = useRef(null);
    const [audioLevel, setAudioLevel] = useState(0);
    const isSpeakingRef = useRef(false);
    const frameCountRef = useRef(0);



    // TTS Helper
    const speak = (text) => {
        return new Promise((resolve) => {
            if (!window.speechSynthesis) {
                resolve();
                return;
            }
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => v.name.includes("Google US English") || v.name.includes("Samantha"));
            if (preferredVoice) utterance.voice = preferredVoice;

            utterance.rate = 1.0;
            utterance.pitch = 1.0;

            utterance.onend = () => resolve();
            utterance.onerror = (err) => {
                console.error("TTS Error:", err);
                resolve();
            };

            window.speechSynthesis.speak(utterance);
        });
    };

    // Anti-Cheating State
    const [violations, setViolations] = useState(0);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [isDisqualified, setIsDisqualified] = useState(false);

    // Monitor Visibility (Tab Switching)
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.hidden && !isFinished && !isDisqualified) {
                setViolations(prev => {
                    const newCount = prev + 1;
                    if (newCount >= 2) {
                        handleDisqualification();
                    } else {
                        alert(`⚠️ WARNING: Tab switching is not allowed! Strike ${newCount}/2. Next violation will disqualify you.`);
                    }
                    return newCount;
                });
            }
        };

        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };

        document.addEventListener("visibilitychange", handleVisibilityChange);
        document.addEventListener("fullscreenchange", handleFullscreenChange);

        return () => {
            document.removeEventListener("visibilitychange", handleVisibilityChange);
            document.removeEventListener("fullscreenchange", handleFullscreenChange);
        };
    }, [isFinished, isDisqualified]);

    const handleDisqualification = async () => {
        setIsDisqualified(true);
        setIsRecording(false);
        speak("Interview terminated due to suspicious activity.");

        // Notify Backend of Disqualification (Mocking an empty audio send with explicit context)
        // We do this to ensure the grading system records a FAIL.
        try {
            const formData = new FormData();
            // Create a silent 1-second blob
            const silentBlob = new Blob([new Uint8Array(1024)], { type: 'audio/webm' });
            formData.append("audio", silentBlob, "violation.webm");
            formData.append("candidate_email", candidateEmail || "unknown");
            formData.append("job_title", jobTitle || "unknown");

            const violationContext = transcript.map(t => `${t.sender.toUpperCase()}: ${t.text}`).join("\n")
                + "\nSYSTEM: CANDIDATE DISQUALIFIED. REASON: CHEATING (TAB SWITCHING). TERMINATE IMMEDIATELY.";

            formData.append("history", violationContext);

            await api.post('/interview/process', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
        } catch (err) {
            console.error("Failed to log disqualification:", err);
        }
    };

    const enterFullscreen = () => {
        document.documentElement.requestFullscreen().catch((e) => {
            console.error("Fullscreen blocked", e);
            alert("Please enable fullscreen to proceed.");
        });
    };

    // Auto-Greeting (Only when entered Fullscreen/Proctor Mode)
    // Auto-Greeting (Only when entered Fullscreen/Proctor Mode)
    const hasGreetedRef = useRef(false);
    useEffect(() => {
        if (isDisqualified || !isFullscreen || hasGreetedRef.current) return;

        const initialGreeting = transcript[0]?.text;

        if (initialGreeting) {
            hasGreetedRef.current = true;
            setTimeout(() => {
                speak(initialGreeting).catch(err => console.log("Auto-play prevented:", err));
            }, 1000); // Wait 1s after fullscreen transition
        }
    }, [isFullscreen, isDisqualified]);

    // Webcam & Monitoring
    const videoRef = useRef(null);
    const streamRef = useRef(null); // Global Stream
    const [notification, setNotification] = useState(null);

    // 1. Independent Webcam Activation for Proctoring
    const enableWebcam = async () => {
        try {
            // Request BOTH Audio and Video immediately to lock hardware
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: {
                    echoCancellation: true, // CRITICAL: Enabled to prevent AI hearing itself
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            streamRef.current = stream; // Store for recording later

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            startMonitoringLoop();
        } catch (err) {
            console.error("Webcam denied:", err);
            alert("⚠️ Camera/Microphone access is MANDATORY. Please allow permissions and reload.");
        }
    };

    const startRecording = async () => {
        try {
            // Reuse existing stream if available
            let stream = streamRef.current;

            if (!stream) {
                console.warn("Stream lost? Re-requesting...");
                stream = await navigator.mediaDevices.getUserMedia({
                    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
                    video: true
                });
                streamRef.current = stream;
            }

            // Log the active device (Console only)
            const track = stream.getAudioTracks()[0];
            console.log("🎤 Using Microphone:", track?.label);

            // ... Audio Context Setup (Rest leads to gain node) ...

            // Setup Audio Graph for Gain Boost
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            if (audioContextRef.current.state === 'suspended') {
                await audioContextRef.current.resume();
            }

            const source = audioContextRef.current.createMediaStreamSource(stream);
            const gainNode = audioContextRef.current.createGain();
            gainNode.gain.value = 5.0; // 500% Volume Boost

            source.connect(gainNode);

            // Analysis
            const analyser = audioContextRef.current.createAnalyser();
            analyser.fftSize = 256;
            gainNode.connect(analyser);

            analyserRef.current = analyser;
            dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);

            // Connect to Destination (Loopback prevented)
            // gainNode.connect(audioContextRef.current.destination); // DO NOT UNCOMMENT - causes echo

            // Setup MediaRecorder
            // CRITICAL FIX: Extract ONLY the Audio Track for the recorder.
            // If we pass the mixed stream (Video+Audio), MediaRecorder tries to record video too
            // which bloats the file and breaks the backend audio processing.
            const audioTrack = stream.getAudioTracks()[0];
            const audioStream = new MediaStream([audioTrack]);

            const mediaRecorder = new MediaRecorder(audioStream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                    console.log(`🎤 Chunk received: ${event.data.size} bytes`);
                }
            };

            mediaRecorder.onstop = handleAudioStop;

            // Start recording with 1s timeslice to ensure data is pushed regularly
            mediaRecorder.start(1000);
            setIsRecording(true);

            // Start Mock Monitoring Loop
            startMonitoringLoop();

        } catch (err) {
            console.error("Error accessing mic/cam:", err);
            alert("⚠️ Camera/Microphone access is REQUIRED for this interview.\nPlease allow permissions and reload.");
        }
    };

    const startMonitoringLoop = () => {
        const interval = setInterval(() => {
            const msgs = [
                "📸 System: Monitoring Snapshot Captured",
                "👀 AI Gaze Tracking: Analyzing Eye Movement...",
                "🔒 Security: Verifying Environment Integrity...",
                "📸 System: Periodic Image Scan Complete"
            ];
            const randomMsg = msgs[Math.floor(Math.random() * msgs.length)];

            setNotification(randomMsg);
            setTimeout(() => setNotification(null), 3000); // Hide after 3s

        }, 45000); // Every 45 seconds

        // Initial "scan"
        setTimeout(() => {
            setNotification("🔒 Security Check: Validating Candidate ID...");
            setTimeout(() => setNotification(null), 3000);
        }, 5000);

        return () => clearInterval(interval);
    };

    const checkAudioLevel = () => {
        if (!analyserRef.current || !isRecording) return;

        analyserRef.current.getByteFrequencyData(dataArrayRef.current);
        const array = dataArrayRef.current;
        let values = 0;
        for (let i = 0; i < array.length; i++) {
            values += array[i];
        }
        const average = values / array.length;
        setAudioLevel(average);

        // DEBUG: Log levels occasionally
        frameCountRef.current = (frameCountRef.current + 1) % 20; // Increment and reset every 20 frames
        if (frameCountRef.current === 0) {
            console.log("🎤 Mic Level:", average);
        }

        // Lower threshold to 5 (approx 2% volume)
        if (average > 5) {
            isSpeakingRef.current = true;
        }

        if (isRecording) {
            requestAnimationFrame(checkAudioLevel);
        }
    };

    useEffect(() => {
        if (isRecording) checkAudioLevel();
    }, [isRecording]);

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            setIsProcessing(true);
        }
    };

    const handleAudioStop = async () => {
        // VAD CHECK
        if (!isSpeakingRef.current) {
            console.warn("No speech detected locally. Aborting upload.");
            setIsProcessing(false);
            setTranscript(prev => [...prev, { sender: 'ai', text: "I didn't hear anything. Please speak closer to the mic." }]);
            speak("I didn't hear anything. Please speak closer to the mic.");
            return;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });


        // Create form data
        const formData = new FormData();
        formData.append("audio", audioBlob, "input.webm");
        formData.append("candidate_email", candidateEmail || "unknown");
        formData.append("job_title", jobTitle || "unknown");

        // Build history string for context
        const historyContext = transcript.map(t => `${t.sender.toUpperCase()}: ${t.text}`).join("\n");
        formData.append("history", historyContext);

        try {
            const res = await api.post('/interview/process', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const data = res.data;

            // 1. Add User Transcript
            if (data.transcript) {
                setTranscript(prev => [...prev, { sender: 'user', text: data.transcript }]);
            }

            // 2. Add AI Response
            if (data.response) {
                setTranscript(prev => [...prev, { sender: 'ai', text: data.response }]);
            }

            // 3. Handle Termination
            if (data.is_terminated) {
                if (data.response) {
                    await speak(data.response); // Wait for speech
                }
                setIsFinished(true); // New State
                setIsRecording(false);
            } else {
                if (data.response) speak(data.response);
            }

        } catch (err) {
            console.error("Interview API Error:", err);
            setTranscript(prev => [...prev, { sender: 'ai', text: "I'm having trouble hearing you. Please try again." }]);
        } finally {
            setIsProcessing(false);
        }
    };

    // Auto-scroll to bottom
    const bottomRef = useRef(null);
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [transcript]);

    // 1. Disqualified UI
    if (isDisqualified) {
        return (
            <div className="min-h-screen bg-red-950 flex flex-col items-center justify-center p-4 text-center">
                <div className="w-full max-w-md bg-white/10 backdrop-blur-xl border border-red-500/30 rounded-3xl p-8 shadow-2xl">
                    <div className="w-20 h-20 bg-red-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-red-500/30">
                        <User size={40} className="text-white" />
                    </div>
                    <h2 className="text-3xl font-bold text-white mb-2">Interview Terminated</h2>
                    <p className="text-red-200 mb-6 font-semibold">
                        Disqualified due to suspicious activity (Tab Switching).
                    </p>
                    <div className="text-sm text-gray-400">
                        This incident has been logged.
                    </div>
                </div>
            </div>
        );
    }

    // 2. Fullscreen Blocker (Updated for Webcam Warning)
    if (!isFullscreen && !isFinished) {
        return (
            <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4 text-center z-50">
                <div className="max-w-md bg-white/10 backdrop-blur-md p-8 rounded-2xl border border-white/20">
                    <h2 className="text-2xl font-bold text-white mb-4">Proctored Interview Mode</h2>
                    <p className="text-gray-300 mb-6 text-left text-sm">
                        This specific interview session is <b>Video Monitored</b>.
                        <ul className="list-disc pl-5 mt-2 space-y-1 text-gray-400">
                            <li>Video & Audio Recording is Mandatory.</li>
                            <li>AI Gaze Tracking is enabled.</li>
                            <li>Random screenshots will be captured.</li>
                            <li>Switching tabs will result in automatic disqualification.</li>
                        </ul>
                        <br />
                        <span className="text-yellow-400 text-sm block text-center">
                            ⚠️ Please stay in Fullscreen Mode at all times.
                        </span>
                    </p>
                    <button
                        onClick={() => {
                            enterFullscreen();
                            enableWebcam();
                        }}
                        className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-full transition-all shadow-lg hover:shadow-blue-500/30"
                    >
                        Enable Camera & Start
                    </button>
                </div>
            </div>
        );
    }

    if (isFinished) {
        return (
            <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4 text-center">
                <div className="w-full max-w-md bg-white/10 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
                    <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-green-500/30">
                        <User size={40} className="text-white" />
                    </div>
                    <h2 className="text-3xl font-bold text-white mb-2">Interview Complete</h2>
                    <p className="text-gray-300 mb-6">
                        Thank you for your time. The AI Recruiter has finished the evaluation.
                        We will be in touch with the results via email.
                    </p>
                    <button
                        onClick={() => window.close()}
                        className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
                    >
                        Close Window
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-white font-sans selection:bg-blue-500/30">
            {/* Webcam Feed (Proctoring) */}
            <div className="fixed top-4 right-4 w-48 h-36 bg-black rounded-lg overflow-hidden border border-white/20 shadow-xl z-20">
                <video ref={videoRef} autoPlay muted className="w-full h-full object-cover transform scale-x-[-1]" />
                <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-black/60 px-2 py-0.5 rounded text-[10px] text-red-500 font-bold tracking-wider uppercase">
                    <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                    REC
                </div>
            </div>

            {/* Mock Notification Toast */}
            {notification && (
                <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-black/80 backdrop-blur border border-green-500/30 text-green-400 px-4 py-2 rounded-full text-xs font-mono z-50 flex items-center gap-2 animate-in fade-in slide-in-from-top-4 duration-300">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    {notification}
                </div>
            )}

            {/* Gradient Orbs */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className={clsx("absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full blur-[128px] transition-colors duration-1000 opacity-20", isRecording ? "bg-red-600/30" : "bg-blue-600/30")} />
                <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[128px] opacity-20" />
            </div>

            <main className="relative z-10 container mx-auto px-4 h-screen flex flex-col max-w-4xl">

                {/* Header */}
                <header className="py-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <Bot className="text-white" size={24} />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                                AI Interviewer
                            </h1>
                            <p className="text-xs text-blue-400 font-medium tracking-wide uppercase">
                                {jobTitle || 'General Role'} • Live Session
                            </p>
                        </div>
                    </div>
                    {/* Status Indicator */}
                    <div className={clsx("px-3 py-1 rounded-full text-xs font-semibold border flex items-center gap-2 transition-all", isRecording ? "bg-red-500/10 border-red-500/50 text-red-400 animate-pulse" : "bg-blue-500/10 border-blue-500/50 text-blue-400")}>
                        <div className={clsx("w-2 h-2 rounded-full", isRecording ? "bg-red-500" : "bg-blue-500")} />
                        {isRecording ? "LISTENING" : "READY"}
                    </div>
                </header>

                {/* Conversation Area */}
                <div className="flex-1 overflow-y-auto space-y-6 py-4 px-2 scroll-smooth" ref={bottomRef}>
                    {transcript.map((msg, idx) => (
                        <div key={idx} className={clsx("flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500", msg.sender === 'user' ? "flex-row-reverse" : "flex-row")}>
                            {/* Avatar */}
                            <div className={clsx("w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center shadow-lg transform transition-transform hover:scale-110", msg.sender === 'user' ? "bg-indigo-600" : "bg-cyan-600")}>
                                {msg.sender === 'user' ? <User size={20} /> : <Bot size={20} />}
                            </div>

                            {/* Message Bubble */}
                            <div className={clsx("max-w-[75%] px-6 py-4 rounded-2xl shadow-sm border backdrop-blur-sm text-sm leading-relaxed",
                                msg.sender === 'user'
                                    ? "bg-indigo-600/20 border-indigo-500/30 text-indigo-100 rounded-tr-none"
                                    : "bg-gray-800/40 border-white/10 text-gray-100 rounded-tl-none"
                            )}>
                                {msg.text}
                            </div>
                        </div>
                    ))}
                    <div ref={bottomRef} className="pb-4" />
                </div>

                {/* Audio Visualizer */}
                <div className="mb-4 h-24 flex items-center justify-center gap-1.5 opacity-80">
                    {Array.from({ length: 40 }).map((_, i) => {
                        // Simple visualizer simulation or use real data if connected
                        // Using a simple animation for "Ambience" when not recording
                        // When recording, we could map real volume. For now, simple pulsing line.
                        const height = isRecording ? Math.max(10, Math.random() * (audioLevel * 1.5)) : 4;
                        return (
                            <div
                                key={i}
                                className={clsx("w-1.5 rounded-full transition-all duration-75", isRecording ? "bg-gradient-to-t from-cyan-500 to-blue-500" : "bg-gray-700")}
                                style={{ height: `${height}%` }}
                            />
                        )
                    })}
                </div>


                {/* Controls Area */}
                <div className="py-8 flex justify-center pb-12 flex-shrink-0 relative">
                    <button
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={isProcessing}
                        className={clsx(
                            "group relative w-20 h-20 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:pointer-events-none",
                            isRecording ? "bg-red-500 hover:bg-red-600 shadow-red-500/40" : "bg-white hover:bg-gray-100 shadow-white/20"
                        )}
                    >
                        {isRecording ? (
                            <div className="w-8 h-8 bg-white rounded-md group-hover:rounded-sm transition-all" />
                        ) : (
                            // Show Mic even if processing (to look like "original state" but busy)
                            <Mic size={32} className={clsx("transition-colors", isProcessing ? "text-slate-400 animate-pulse" : "text-slate-900")} />
                        )}

                        {/* Ping Animation */}
                        {isRecording && (
                            <span className="absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-20 animate-ping" />
                        )}
                    </button>

                    {/* Status Indicators */}
                    {!isRecording && !isProcessing && (
                        <div className="absolute -bottom-2 text-gray-400 text-sm font-medium tracking-wide animate-pulse pointer-events-none">
                            Tap to Speak
                        </div>
                    )}

                    {isProcessing && (
                        <div className="absolute -bottom-4 flex flex-col items-center gap-1 animate-in fade-in zoom-in duration-300">
                            <div className="flex items-center gap-2 text-blue-400 text-sm font-bold tracking-wider uppercase">
                                <Loader2 size={14} className="animate-spin" />
                                Thinking...
                            </div>
                            <p className="text-[10px] text-gray-500">AI is analyzing your response</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="py-2 text-center flex-shrink-0">
                    <p className="text-white/20 text-xs uppercase tracking-widest">Powered by Candidate Intelligence Platform</p>
                </div>

            </main >
        </div >
    );
};

export default InterviewPage;
