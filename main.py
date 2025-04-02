from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import json
import logging
import tempfile
import os
import base64
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your OpenAI API keys
WHISPER_API_KEY = "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"
GPT_API_KEY = WHISPER_API_KEY  # Using the same key for both services

# Create FastAPI app
app = FastAPI()

# HTML content with embedded JavaScript - be careful to properly close the triple quotes
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smartsphere Technologies</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2 {
            text-align: center;
            color: #333;
        }
        .status {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .connecting {
            background-color: #fff9c4;
            border: 1px solid #fbc02d;
        }
        .connected {
            background-color: #c8e6c9;
            border: 1px solid #4caf50;
            display: none;
        }
        .disconnected {
            background-color: #ffcdd2;
            border: 1px solid #e53935;
            display: none;
        }
        .content-box {
            height: 300px;
            overflow-y: auto;
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        #transcript {
            background-color: #f9f9f9;
        }
        #summary {
            border-color: #2196f3;
            background-color: #e3f2fd;
        }
        #minutes {
            border-color: #4caf50;
            background-color: #e8f5e9;
        }
        #agenda {
            border-color: #ff9800;
            background-color: #fff3e0;
        }
        #next-steps {
            border-color: #9c27b0;
            background-color: #f3e5f5;
        }
        #tasks {
            border-color: #f44336;
            background-color: #ffebee;
        }
        .user-message {
            margin: 8px 0;
            padding: 8px;
            border-radius: 8px;
            background-color: #e3f2fd;
        }
        .assistant-message {
            margin: 8px 0;
            padding: 8px;
            border-radius: 8px;
            background-color: #f1f1f1;
        }
        .content-wrapper {
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            background-color: #fff;
            border-left: 4px solid #2196f3;
        }
        .minutes-content {
            border-left-color: #4caf50;
        }
        .agenda-content {
            border-left-color: #ff9800;
        }
        .next-steps-content {
            border-left-color: #9c27b0;
        }
        .tasks-content {
            border-left-color: #f44336;
        }
        .controls {
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
            align-items: center;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            background-color: #2196f3;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background-color: #1976d2;
        }
        button:disabled {
            background-color: #bdbdbd;
            cursor: not-allowed;
        }
        .record-button {
            background-color: #f44336;
        }
        .record-button:hover {
            background-color: #d32f2f;
        }
        .record-button.recording {
            animation: pulse 1.5s infinite;
        }
        .download-options {
            position: absolute;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            padding: 10px;
            z-index: 10;
            display: none;
        }
        .download-option {
            display: block;
            width: 100%;
            text-align: left;
            padding: 8px 10px;
            background: none;
            border: none;
            cursor: pointer;
            color: #333;
            margin: 2px 0;
            border-radius: 3px;
        }
        .download-option:hover {
            background-color: #f5f5f5;
        }
        .language-selector {
            margin-bottom: 20px;
            text-align: center;
        }
        select {
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #ddd;
            font-size: 16px;
        }
        @keyframes pulse {
            0% { background-color: #f44336; }
            50% { background-color: #d32f2f; }
            100% { background-color: #f44336; }
        }
        .timer {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 24px;
            font-weight: bold;
            font-family: monospace;
            color: #333;
            text-align: center;
            min-width: 120px;
        }
        .loading {
            text-align: center;
            margin: 20px 0;
            font-style: italic;
            color: #666;
            display: none;
        }
        .tabs {
            display: flex;
            flex-wrap: wrap;
            margin: 20px 0;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 15px;
            cursor: pointer;
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-bottom: none;
            margin-right: 3px;
            margin-bottom: -1px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            font-size: 14px;
        }
        .tab.active {
            background-color: #fff;
            border-bottom: 1px solid #fff;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .dropdown {
            position: relative;
            display: inline-block;
        }
        .dropdown-content {
            display: none;
            position: absolute;
            right: 0;
            background-color: #f9f9f9;
            min-width: 200px;
            box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
            z-index: 1;
            border-radius: 5px;
        }
        .dropdown:hover .dropdown-content {
            display: block;
        }
        .processing-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 15px;
            margin: 10px 0;
            background-color: #f5f5f5;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            border-radius: 50%;
            border-top: 4px solid #3498db;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <h1>Smartsphere Technologies Meeting-Note-Taker</h1>
    
    <div id="connecting" class="status connecting">
        <p>Initializing transcription service...</p>
    </div>
    
    <div id="connected" class="status connected">
        <p>Connected. Ready to transcribe.</p>
    </div>
    
    <div id="disconnected" class="status disconnected">
        <p>Disconnected from transcription service.</p>
    </div>
    
    <div class="language-selector">
        <label for="language">Language: </label>
        <select id="language">
            <option value="en" selected>English</option>
            <option value="ur">Urdu</option>
        </select>
    </div>
    
    <div class="controls">
        <button id="recordButton" class="record-button" disabled>Start Recording</button>
        <div id="timer" class="timer">00:00:00</div>
        <div class="dropdown">
            <button id="downloadButton" disabled>Download</button>
            <div class="dropdown-content">
                <button id="downloadTranscriptBtn" class="download-option">Transcript Only</button>
                <button id="downloadSummaryBtn" class="download-option">Summary Only</button>
                <button id="downloadMinutesBtn" class="download-option">Minutes Only</button>
                <button id="downloadAgendaBtn" class="download-option">Agenda Only</button>
                <button id="downloadNextStepsBtn" class="download-option">Next Steps Only</button>
                <button id="downloadTasksBtn" class="download-option">Tasks Only</button>
                <button id="downloadCompleteBtn" class="download-option">Complete Report</button>
            </div>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" data-tab="transcript">Transcript</div>
        <div class="tab" data-tab="summary">Summary</div>
        <div class="tab" data-tab="minutes">Minutes</div>
        <div class="tab" data-tab="agenda">Agenda</div>
        <div class="tab" data-tab="next-steps">Next Steps</div>
        <div class="tab" data-tab="tasks">Task Allocation</div>
    </div>
    
    <div id="transcript-tab" class="tab-content active">
        <div id="transcript" class="content-box"></div>
    </div>
    
    <div id="summary-tab" class="tab-content">
        <div id="summary-loading" class="loading">
            <div class="processing-indicator">
                <div class="spinner"></div>
                <span>Generating meeting summary...</span>
            </div>
        </div>
        <div id="summary" class="content-box"></div>
    </div>
    
    <div id="minutes-tab" class="tab-content">
        <div id="minutes-loading" class="loading">
            <div class="processing-indicator">
                <div class="spinner"></div>
                <span>Generating meeting minutes...</span>
            </div>
        </div>
        <div id="minutes" class="content-box"></div>
    </div>
    
    <div id="agenda-tab" class="tab-content">
        <div id="agenda-loading" class="loading">
            <div class="processing-indicator">
                <div class="spinner"></div>
                <span>Identifying agenda items...</span>
            </div>
        </div>
        <div id="agenda" class="content-box"></div>
    </div>
    
    <div id="next-steps-tab" class="tab-content">
        <div id="next-steps-loading" class="loading">
            <div class="processing-indicator">
                <div class="spinner"></div>
                <span>Identifying next steps...</span>
            </div>
        </div>
        <div id="next-steps" class="content-box"></div>
    </div>
    
    <div id="tasks-tab" class="tab-content">
        <div id="tasks-loading" class="loading">
            <div class="processing-indicator">
                <div class="spinner"></div>
                <span>Identifying task allocations...</span>
            </div>
        </div>
        <div id="tasks" class="content-box"></div>
    </div>
    
    <script>
        // DOM elements
        const connectingStatus = document.getElementById('connecting');
        const connectedStatus = document.getElementById('connected');
        const disconnectedStatus = document.getElementById('disconnected');
        const transcriptDiv = document.getElementById('transcript');
        const summaryDiv = document.getElementById('summary');
        const minutesDiv = document.getElementById('minutes');
        const agendaDiv = document.getElementById('agenda');
        const nextStepsDiv = document.getElementById('next-steps');
        const tasksDiv = document.getElementById('tasks');
        
        const summaryLoading = document.getElementById('summary-loading');
        const minutesLoading = document.getElementById('minutes-loading');
        const agendaLoading = document.getElementById('agenda-loading');
        const nextStepsLoading = document.getElementById('next-steps-loading');
        const tasksLoading = document.getElementById('tasks-loading');
        
        const recordButton = document.getElementById('recordButton');
        const downloadButton = document.getElementById('downloadButton');
        const downloadTranscriptBtn = document.getElementById('downloadTranscriptBtn');
        const downloadSummaryBtn = document.getElementById('downloadSummaryBtn');
        const downloadMinutesBtn = document.getElementById('downloadMinutesBtn');
        const downloadAgendaBtn = document.getElementById('downloadAgendaBtn');
        const downloadNextStepsBtn = document.getElementById('downloadNextStepsBtn');
        const downloadTasksBtn = document.getElementById('downloadTasksBtn');
        const downloadCompleteBtn = document.getElementById('downloadCompleteBtn');
        
        const languageSelect = document.getElementById('language');
        const timerElement = document.getElementById('timer');
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');
        
        // WebSocket URL
        const socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/transcribe`;
        let socket;
        
        // Audio context and recorder variables
        let audioContext;
        let recorder;
        let isRecording = false;
        let gumStream;
        
        // Timer variables
        let startTime;
        let timerInterval;
        let recordingDuration = "00:00:00";
        
        // Transcript and generated content storage
        let fullTranscript = [];
        let meetingSummary = "";
        let meetingMinutes = "";
        let meetingAgenda = "";
        let meetingNextSteps = "";
        let meetingTasks = "";
        let meetingDate = new Date();
        
        // Initialize WebSocket connection
        function connectWebSocket() {
            socket = new WebSocket(socketUrl);
            
            socket.onopen = () => {
                console.log('WebSocket connection established');
                connectingStatus.style.display = 'none';
                connectedStatus.style.display = 'block';
                disconnectedStatus.style.display = 'none';
                recordButton.disabled = false;
            };
            
            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('Received message:', data);
                    
                    if (data.type === 'transcript') {
                        // Filter out single-word responses like "you"
                        if (data.text && data.text.trim() && data.text.trim().split(/\\s+/).length > 1) {
                            addMessageToTranscript('user', data.text);
                            fullTranscript.push(data.text);
                            downloadButton.disabled = false;
                            downloadTranscriptBtn.disabled = false;
                        } else {
                            console.log('Filtered out short response:', data.text);
                        }
                    } else if (data.type === 'summary') {
                        meetingSummary = data.text;
                        addContentToDiv(summaryDiv, data.text);
                        summaryLoading.style.display = 'none';
                        downloadSummaryBtn.disabled = false;
                    } else if (data.type === 'minutes') {
                        meetingMinutes = data.text;
                        addContentToDiv(minutesDiv, data.text, 'minutes-content');
                        minutesLoading.style.display = 'none';
                        downloadMinutesBtn.disabled = false;
                    } else if (data.type === 'agenda') {
                        meetingAgenda = data.text;
                        addContentToDiv(agendaDiv, data.text, 'agenda-content');
                        agendaLoading.style.display = 'none';
                        downloadAgendaBtn.disabled = false;
                    } else if (data.type === 'next_steps') {
                        meetingNextSteps = data.text;
                        addContentToDiv(nextStepsDiv, data.text, 'next-steps-content');
                        nextStepsLoading.style.display = 'none';
                        downloadNextStepsBtn.disabled = false;
                    } else if (data.type === 'tasks') {
                        meetingTasks = data.text;
                        addContentToDiv(tasksDiv, data.text, 'tasks-content');
                        tasksLoading.style.display = 'none';
                        downloadTasksBtn.disabled = false;
                    } else if (data.type === 'processing_complete') {
                        downloadCompleteBtn.disabled = false;
                    }
                } catch (error) {
                    console.error('Error processing message:', error);
                }
            };
            
            socket.onclose = () => {
                console.log('WebSocket connection closed');
                connectingStatus.style.display = 'none';
                connectedStatus.style.display = 'none';
                disconnectedStatus.style.display = 'block';
                recordButton.disabled = true;
                stopRecording();
            };
            
            socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                connectingStatus.style.display = 'none';
                connectedStatus.style.display = 'none';
                disconnectedStatus.style.display = 'block';
            };
        }
        
        // Tab functionality
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Remove active class from all tabs
                tabs.forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                tab.classList.add('active');
                
                // Hide all tab contents
                tabContents.forEach(tc => tc.classList.remove('active'));
                
                // Show the corresponding tab content
                const tabId = tab.getAttribute('data-tab');
                document.getElementById(tabId + '-tab').classList.add('active');
            });
        });
        
        // Add message to transcript display
        function addMessageToTranscript(role, content) {
            if (!content || !content.trim()) return;
            
            const message = document.createElement('p');
            message.className = role === 'user' ? 'user-message' : 'assistant-message';
            
            const label = role === 'user' ? 'Transcription' : 'Assistant';
            message.innerHTML = `<strong>${label}:</strong> ${content}`;
            
            transcriptDiv.appendChild(message);
            transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
        }
        
        // Add content to a div
        function addContentToDiv(div, content, contentClass = 'content-wrapper') {
            if (!content || !content.trim()) return;
            
            div.innerHTML = '';
            
            const wrapper = document.createElement('div');
            wrapper.className = contentClass;
            wrapper.innerHTML = content;
            
            div.appendChild(wrapper);
        }
        
        // Format date for file names and headers
        function formatDate(date) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            
            return `${year}-${month}-${day}_${hours}-${minutes}`;
        }
        
        // Format date for report header
        function formatDateReadable(date) {
            const options = { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            };
            return date.toLocaleDateString('en-US', options);
        }
        
        // Start the timer
        function startTimer() {
            startTime = Date.now();
            timerElement.textContent = '00:00:00';
            
            timerInterval = setInterval(() => {
                updateTimer();
            }, 1000);
        }
        
        // Update the timer display
        function updateTimer() {
            if (!isRecording) return;
            
            const now = Date.now();
            const elapsedMs = now - startTime;
            
            const hours = Math.floor(elapsedMs / (1000 * 60 * 60));
            const minutes = Math.floor((elapsedMs % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((elapsedMs % (1000 * 60)) / 1000);
            
            const formattedTime = 
                String(hours).padStart(2, '0') + ':' +
                String(minutes).padStart(2, '0') + ':' +
                String(seconds).padStart(2, '0');
            
            recordingDuration = formattedTime;
            timerElement.textContent = formattedTime;
        }
        
        // Stop the timer
        function stopTimer() {
            clearInterval(timerInterval);
        }
        
        // Start recording audio
        function startRecording() {
            console.log('Starting recording...');
            
            // Reset transcript and content
            fullTranscript = [];
            transcriptDiv.innerHTML = '';
            summaryDiv.innerHTML = '';
            minutesDiv.innerHTML = '';
            agendaDiv.innerHTML = '';
            nextStepsDiv.innerHTML = '';
            tasksDiv.innerHTML = '';
            
            meetingSummary = "";
            meetingMinutes = "";
            meetingAgenda = "";
            meetingNextSteps = "";
            meetingTasks = "";
            meetingDate = new Date();
            
            // Disable download buttons
            downloadButton.disabled = true;
            downloadTranscriptBtn.disabled = true;
            downloadSummaryBtn.disabled = true;
            downloadMinutesBtn.disabled = true;
            downloadAgendaBtn.disabled = true;
            downloadNextStepsBtn.disabled = true;
            downloadTasksBtn.disabled = true;
            downloadCompleteBtn.disabled = true;
            
            const constraints = { audio: true, video: false };
            
            navigator.mediaDevices.getUserMedia(constraints)
                .then(function(stream) {
                    gumStream = stream;
                    
                    // Create AudioContext
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    
                    // Create ScriptProcessorNode for recording
                    const bufferSize = 4096;
                    const numberOfInputChannels = 1;
                    const numberOfOutputChannels = 1;
                    
                    // Create and configure recorder
                    recorder = audioContext.createScriptProcessor(
                        bufferSize, numberOfInputChannels, numberOfOutputChannels
                    );
                    
                    // Create source from the audio stream
                    const source = audioContext.createMediaStreamSource(stream);
                    source.connect(recorder);
                    recorder.connect(audioContext.destination);
                    
                    // Start recording
                    isRecording = true;
                    recordButton.textContent = 'Stop Recording';
                    recordButton.classList.add('recording');
                    
                    // Start the timer
                    startTimer();
                    
                    // Variables for recording
                    let recordingBuffer = [];
                    let recordingLength = 0;
                    let lastSendTime = Date.now();
                    const sendInterval = 5000; // Send every 5 seconds
                    
                    // Process audio data
                    recorder.onaudioprocess = function(e) {
                        if (!isRecording) return;
                        
                        // Get the audio data
                        const buffer = e.inputBuffer.getChannelData(0);
                        const newBuffer = new Float32Array(buffer);
                        
                        // Add to recording buffer
                        recordingBuffer.push(newBuffer);
                        recordingLength += newBuffer.length;
                        
                        // Check if it's time to send audio
                        const now = Date.now();
                        if (now - lastSendTime >= sendInterval) {
                            sendAudioData(recordingBuffer, recordingLength);
                            
                            // Reset buffers but keep a small overlap
                            recordingBuffer = [];
                            recordingLength = 0;
                            lastSendTime = now;
                        }
                    };
                    
                    console.log('Recording started');
                })
                .catch(function(err) {
                    console.error('Could not start recording:', err);
                    alert('Could not start recording: ' + err.message);
                });
        }
        
        // Send audio data to server
        function sendAudioData(buffers, length) {
            console.log('Sending audio data, length:', length);
            
            // Create a new buffer to store the entire recording
            const fullBuffer = new Float32Array(length);
            let offset = 0;
            
            // Copy all buffers into the full buffer
            for (let i = 0; i < buffers.length; i++) {
                fullBuffer.set(buffers[i], offset);
                offset += buffers[i].length;
            }
            
            // Convert to 16-bit PCM WAV format
            const wavData = encodeWAV(fullBuffer, audioContext.sampleRate);
            const wavBlob = new Blob([wavData], { type: 'audio/wav' });
            
            // Convert WAV blob to base64
            const reader = new FileReader();
            reader.onload = function() {
                const base64data = reader.result.split(',')[1];
                
                // Send to server
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({
                        audio: base64data,
                        language: languageSelect.value,
                        format: 'audio/wav'
                    }));
                    console.log('Audio data sent');
                } else {
                    console.error('WebSocket not open');
                }
            };
            
            reader.readAsDataURL(wavBlob);
        }
        
        // Generate meeting documentation
        function generateMeetingDocumentation() {
            if (fullTranscript.length === 0) {
                return;
            }
            
            // Show all loading indicators
            summaryLoading.style.display = 'block';
            minutesLoading.style.display = 'block';
            agendaLoading.style.display = 'block';
            nextStepsLoading.style.display = 'block';
            tasksLoading.style.display = 'block';
            
            // Send request for generation
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'generate_documentation',
                    transcript: fullTranscript.join('\\n')
                }));
                console.log('Documentation generation request sent');
            } else {
                console.error('WebSocket not open');
                hideAllLoadingIndicators();
            }
        }
        
        function hideAllLoadingIndicators() {
            summaryLoading.style.display = 'none';
            minutesLoading.style.display = 'none';
            agendaLoading.style.display = 'none';
            nextStepsLoading.style.display = 'none';
            tasksLoading.style.display = 'none';
        }
        
        // Convert Float32Array to WAV format
        function encodeWAV(samples, sampleRate) {
            const buffer = new ArrayBuffer(44 + samples.length * 2);
            const view = new DataView(buffer);
            
            // Write the file header
            writeString(view, 0, 'RIFF');
            view.setUint32(4, 36 + samples.length * 2, true);
            writeString(view, 8, 'WAVE');
            writeString(view, 12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, 1, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            writeString(view, 36, 'data');
            view.setUint32(40, samples.length * 2, true);
            
            // Convert Float32 to Int16
            floatTo16BitPCM(view, 44, samples);
            
            return view;
        }
        

        
        // Convert floating point samples to 16-bit PCM
        function floatTo16BitPCM(output, offset, input) {
            for (let i = 0; i < input.length; i++, offset += 2) {
                const s = Math.max(-1, Math.min(1, input[i]));
                output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
        }
        
        // Write a string to a DataView at specified offset
        function writeString(view, offset, string) {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        }
        
        // Stop recording audio
        function stopRecording() {
            if (isRecording) {
                console.log('Stopping recording...');
                
                // Stop recording
                isRecording = false;
                
                // Stop the timer
                stopTimer();
                
                // Stop microphone access
                if (gumStream) {
                    gumStream.getAudioTracks().forEach(track => {
                        track.stop();
                    });
                }
                
                // Disconnect recorder
                if (recorder) {
                    recorder.disconnect();
                }
                
                // Clean up AudioContext
                if (audioContext && audioContext.state !== 'closed') {
                    audioContext.close().then(() => {
                        console.log('AudioContext closed');
                    });
                }
                
                recordButton.textContent = 'Start Recording';
                recordButton.classList.remove('recording');
                
                console.log('Recording stopped');
                
                // Generate meeting documentation
                if (fullTranscript.length > 0) {
                    downloadButton.disabled = false;
                    downloadTranscriptBtn.disabled = false;
                    generateMeetingDocumentation();
                }
            }
        }
        
        // Toggle recording state
        function toggleRecording() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        // Download transcript only
        function downloadTranscriptOnly() {
            const transcriptText = fullTranscript.join('\\n\\n');
            
            if (!transcriptText.trim()) {
                alert('No transcription to download yet.');
                return;
            }
            
            const blob = new Blob([transcriptText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `transcript_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Download summary only
        function downloadSummaryOnly() {
            if (!meetingSummary.trim()) {
                alert('No summary available yet.');
                return;
            }
            
            const blob = new Blob([meetingSummary], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `summary_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Download minutes only
        function downloadMinutesOnly() {
            if (!meetingMinutes.trim()) {
                alert('No minutes available yet.');
                return;
            }
            
            const blob = new Blob([meetingMinutes], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `minutes_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Download agenda only
        function downloadAgendaOnly() {
            if (!meetingAgenda.trim()) {
                alert('No agenda available yet.');
                return;
            }
            
            const blob = new Blob([meetingAgenda], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `agenda_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Download next steps only
        function downloadNextStepsOnly() {
            if (!meetingNextSteps.trim()) {
                alert('No next steps available yet.');
                return;
            }
            
            const blob = new Blob([meetingNextSteps], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `next_steps_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Download tasks only
        function downloadTasksOnly() {
            if (!meetingTasks.trim()) {
                alert('No task allocations available yet.');
                return;
            }
            
            const blob = new Blob([meetingTasks], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `tasks_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Download complete report
        function downloadCompleteReport() {
            const transcriptText = fullTranscript.join('\\n\\n');
            
            if (!transcriptText.trim()) {
                alert('No transcription to download yet.');
                return;
            }
            
            // Format the complete report
            let reportContent = `MEETING REPORT\n`;
            reportContent += `=============\n\n`;
            reportContent += `Date: ${formatDateReadable(meetingDate)}\n`;
            reportContent += `Duration: ${recordingDuration}\n`;
            reportContent += `Language: ${languageSelect.options[languageSelect.selectedIndex].text}\n\n`;
            
            // Add agenda if available
            if (meetingAgenda.trim()) {
                reportContent += `AGENDA\n`;
                reportContent += `======\n\n`;
                reportContent += `${meetingAgenda}\n\n`;
            }
            
            // Add minutes if available
            if (meetingMinutes.trim()) {
                reportContent += `MEETING MINUTES\n`;
                reportContent += `===============\n\n`;
                reportContent += `${meetingMinutes}\n\n`;
            }
            
            // Add summary if available
            if (meetingSummary.trim()) {
                reportContent += `MEETING SUMMARY\n`;
                reportContent += `===============\n\n`;
                reportContent += `${meetingSummary}\n\n`;
            }
            
            // Add next steps if available
            if (meetingNextSteps.trim()) {
                reportContent += `NEXT STEPS\n`;
                reportContent += `==========\n\n`;
                reportContent += `${meetingNextSteps}\n\n`;
            }
            
            // Add task allocations if available
            if (meetingTasks.trim()) {
                reportContent += `TASK ALLOCATIONS\n`;
                reportContent += `================\n\n`;
                reportContent += `${meetingTasks}\n\n`;
            }
            
            // Add full transcript
            reportContent += `FULL TRANSCRIPT\n`;
            reportContent += `===============\n\n`;
            reportContent += transcriptText;
            
            const blob = new Blob([reportContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `meeting_report_${formatDate(meetingDate)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Event listeners
        recordButton.addEventListener('click', toggleRecording);
        downloadTranscriptBtn.addEventListener('click', downloadTranscriptOnly);
        downloadSummaryBtn.addEventListener('click', downloadSummaryOnly);
        downloadMinutesBtn.addEventListener('click', downloadMinutesOnly);
        downloadAgendaBtn.addEventListener('click', downloadAgendaOnly);
        downloadNextStepsBtn.addEventListener('click', downloadNextStepsOnly);
        downloadTasksBtn.addEventListener('click', downloadTasksOnly);
        downloadCompleteBtn.addEventListener('click', downloadCompleteReport);
        
        // Initialize connection when page loads
        window.addEventListener('load', connectWebSocket);
    </script>
</body>
</html>"""

class TranscriptionWebSocket:
    """WebSocket wrapper to handle transcription processing"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.transcript = []
        
    async def handle(self):
        """Process incoming audio and manage transcription"""
        await self.websocket.accept()
        logger.info("WebSocket connection accepted")
        
        try:
            while True:
                # Receive data from client
                data = await self.websocket.receive_text()
                logger.info(f"Received WebSocket data of length: {len(data)}")
                
                try:
                    # Parse the JSON data
                    message = json.loads(data)
                    
                    # Handle audio transcription
                    if 'audio' in message:
                        audio_data = message.get('audio')
                        language = message.get('language', '')
                        
                        if audio_data:
                            logger.info(f"Processing audio with language: {language}")
                            
                            # Process audio with Whisper
                            transcript = await self.transcribe_audio(audio_data, language)
                            
                            # Filter out very short responses
                            words = transcript.strip().split()
                            if transcript and len(words) > 1:
                                logger.info(f"Transcription result: {transcript}")
                                
                                # Send transcription back to client
                                await self.websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript
                                })
                                
                                # Add to transcript history
                                self.transcript.append({"role": "user", "content": transcript})
                            else:
                                logger.warning(f"Filtered out short transcription: {transcript}")
                    
                    # Handle meeting documentation generation request
                    elif message.get('type') == 'generate_documentation':
                        transcript_text = message.get('transcript', '')
                        
                        if transcript_text:
                            logger.info("Generating meeting documentation")
                            
                            # Generate summary
                            summary = await self.generate_summary(transcript_text)
                            if summary:
                                await self.websocket.send_json({
                                    "type": "summary",
                                    "text": summary
                                })
                            
                            # Generate minutes
                            minutes = await self.generate_minutes(transcript_text)
                            if minutes:
                                await self.websocket.send_json({
                                    "type": "minutes",
                                    "text": minutes
                                })
                            
                            # Generate agenda
                            agenda = await self.generate_agenda(transcript_text)
                            if agenda:
                                await self.websocket.send_json({
                                    "type": "agenda",
                                    "text": agenda
                                })
                            
                            # Generate next steps
                            next_steps = await self.generate_next_steps(transcript_text)
                            if next_steps:
                                await self.websocket.send_json({
                                    "type": "next_steps",
                                    "text": next_steps
                                })
                            
                            # Generate tasks
                            tasks = await self.generate_tasks(transcript_text)
                            if tasks:
                                await self.websocket.send_json({
                                    "type": "tasks",
                                    "text": tasks
                                })
                            
                            # Notify client that all processing is complete
                            await self.websocket.send_json({
                                "type": "processing_complete"
                            })
                
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON message")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    await self.websocket.send_json({
                        "type": "transcript",
                        "text": f"Error: {str(e)[:100]}"
                    })
        
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {str(e)}")
    
    async def transcribe_audio(self, base64_audio, language=None):
        """Transcribe audio using OpenAI's Whisper API directly"""
        temp_file = None
        file_obj = None
        
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(base64_audio)
            logger.info(f"Decoded audio data length: {len(audio_data)} bytes")
            
            # Create unique filename
            timestamp = str(int(time.time() * 1000))
            random_suffix = os.urandom(4).hex()
            temp_file = os.path.join(tempfile.gettempdir(), f"audio_{timestamp}_{random_suffix}.wav")
            
            # Save WAV file
            with open(temp_file, 'wb') as f:
                f.write(audio_data)
            logger.info(f"Saved audio to file: {temp_file}")
            
            # Prepare API call
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {WHISPER_API_KEY}"}
            
            # Open the file for the API request
            file_obj = open(temp_file, 'rb')
            
            # Create form data with file
            files = {
                'file': (os.path.basename(temp_file), file_obj, 'audio/wav'),
                'model': (None, 'whisper-1'),
                'response_format': (None, 'json')
            }
            
            # Add language if specified
            if language:
                files['language'] = (None, language)
            
            # Call Whisper API
            logger.info(f"Sending request to Whisper API with file: {temp_file}")
            response = requests.post(url, headers=headers, files=files)
            logger.info(f"Whisper API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Whisper API error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code} - {response.text[:100]}"
            
            result = response.json()
            return result.get('text', '')
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return f"Error: {str(e)}"
            
        finally:
            # Close the file object first
            if file_obj:
                file_obj.close()
            
            # Then try to delete the temp file
            try:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not remove temporary file: {str(e)}")
    
    async def generate_summary(self, transcript_text):
        """Generate a meeting summary using GPT"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GPT_API_KEY}"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that creates concise and well-structured summaries of meeting transcripts."},
                    {"role": "user", "content": f"Please provide a summary of the following meeting transcript. Focus on key points, important decisions, and overall theme. Format the summary with clear headings and bullet points for readability.\n\nTRANSCRIPT:\n{transcript_text}"}
                ],
                "temperature": 0.5
            }
            
            logger.info("Sending request to GPT API for summary")
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"GPT API response status for summary: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"GPT API error for summary: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Summary generation error: {str(e)}")
            return None
    
    async def generate_minutes(self, transcript_text):
        """Generate meeting minutes using GPT"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GPT_API_KEY}"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a skilled meeting secretary that creates detailed and well-structured meeting minutes."},
                    {"role": "user", "content": f"Please provide detailed minutes for the following meeting transcript. Include attendees (if mentioned), key discussion points, and decisions made. Format it in a professional manner with appropriate headings and bullet points.\n\nTRANSCRIPT:\n{transcript_text}"}
                ],
                "temperature": 0.5
            }
            
            logger.info("Sending request to GPT API for minutes")
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"GPT API response status for minutes: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"GPT API error for minutes: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Minutes generation error: {str(e)}")
            return None
    
    async def generate_agenda(self, transcript_text):
        """Extract or infer agenda items from the meeting transcript"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GPT_API_KEY}"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that can identify the agenda topics from meeting transcripts."},
                    {"role": "user", "content": f"Based on the following meeting transcript, identify the main agenda items that were discussed. If the agenda is explicitly mentioned, extract those items. If not, infer the main topics discussed and create a structured agenda. Format as a numbered list with brief descriptions.\n\nTRANSCRIPT:\n{transcript_text}"}
                ],
                "temperature": 0.5
            }
            
            logger.info("Sending request to GPT API for agenda")
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"GPT API response status for agenda: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"GPT API error for agenda: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Agenda extraction error: {str(e)}")
            return None
    
    async def generate_next_steps(self, transcript_text):
        """Identify next steps from the meeting transcript"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GPT_API_KEY}"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that extracts next steps and action items from meeting transcripts."},
                    {"role": "user", "content": f"Based on the following meeting transcript, identify all the next steps, action items, and follow-ups that were discussed. Format them as a clear, bulleted list with timelines if mentioned. Make sure to highlight who is responsible for each item if that was specified.\n\nTRANSCRIPT:\n{transcript_text}"}
                ],
                "temperature": 0.5
            }
            
            logger.info("Sending request to GPT API for next steps")
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"GPT API response status for next steps: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"GPT API error for next steps: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Next steps extraction error: {str(e)}")
            return None
    
    async def generate_tasks(self, transcript_text):
        """Identify task allocations from the meeting transcript"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GPT_API_KEY}"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that identifies and organizes task allocations from meeting transcripts."},
                    {"role": "user", "content": f"Based on the following meeting transcript, identify all tasks that were assigned to specific people or teams. Organize them by person/team, and include deadlines if mentioned. Format the results as a clear, structured list showing who is responsible for what and by when.\n\nTRANSCRIPT:\n{transcript_text}"}
                ],
                "temperature": 0.5
            }
            
            logger.info("Sending request to GPT API for task allocations")
            response = requests.post(url, headers=headers, json=data)
            logger.info(f"GPT API response status for task allocations: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"GPT API error for task allocations: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Task allocation extraction error: {str(e)}")
            return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Return the HTML page for transcription"""
    return HTMLResponse(content=HTML_CONTENT)

@app.websocket("/transcribe")
async def transcribe(websocket: WebSocket):
    """WebSocket endpoint for transcription"""
    handler = TranscriptionWebSocket(websocket)
    await handler.handle()

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render uses PORT env
    uvicorn.run(app, host="0.0.0.0", port=port)
