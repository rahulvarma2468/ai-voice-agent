

# 🎙 AI Voice Conversation Agent

This is my personal build of an **AI-powered web voice assistant** — an app that listens to what I say, understands it, and talks back in a natural voice.  
It’s the *Day 13 milestone* of my **#30DaysOfAIVoiceents journey, where I’m steadily shaping this project into a polished, working product.


## 🚀 What This Project Does

- Hit **one record button**, speak, and let the agent process your words.
- Speech is converted to text (STT), sent to an LLM for generating a reply.
- The reply is displayed in a **chat bubble** *and* spoken back to you instantly (TTS).
- The UI keeps a full conversation history in the browser.

I wanted this to feel like chatting with a virtual buddy — minimal clicks, maximum flow.

***

## 🧩 How I Built It

**Frontend:**  
- Plain HTML, CSS & JavaScript (no frameworks — kept it light and fast).  
- Single‑toggle mic button with animated pulse while recording.  
- Chat bubble design for clear user/AI separation.  

**Backend:**  
- **FastAPI** (Python) handling audio uploads & AI responses.  
- Routes for processing audio and returning text + audio.  

**AI Services:**  
- **AssemblyAI** – Speech‑to‑Text  
- **Google Gemini** – Conversation generation  
- **Murf API** – Text‑to‑Speech  



## 🗺 Quick Architecture


Browser (Record Audio)  
   ↓
FastAPI Backend
   ↓
[AssemblyAI] → Converts Speech → Text  
[Gemini API] → Generates AI Reply  
[Murf API] → Converts Text → Voice  
   ↓
Browser (Show reply + Play audio)




## ✨ Features I’m Proud Of

- 🎤 **One‑Button Recording** → Start/Stop in the same button.  
- 💬 **Live Chat History** → Keeps both my words and AI’s words visible.  
- 🔊 **Auto Audio Playback** → I don’t have to press play.  
- 🎨 **Custom Background & Glass Look** → My own style, no templates.  
- ⚡ **Responsive Flow** → Few seconds from my voice to AI’s reply.  



## 🛠 Running It on Your System

**1. Clone the repo**

git clone 
cd 


**2. Install the Python dependencies**

pip install -r requirements.txt


**3. Create a `.env` file** in the project root with:

MURF_API_KEY=your_murf_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
GEMINI_API_KEY=your_gemini_key


**4. Start the FastAPI server**

uvicorn app:app --reload


**5. Open** `http://localhost:8000` in your browser.


## 🔑 Environment Variables

| Variable             | Purpose                  |
|----------------------|--------------------------|
| `MURF_API_KEY`       | Text‑to‑Speech            |
| `ASSEMBLYAI_API_KEY` | Speech‑to‑Text            |
| `GEMINI_API_KEY`     | LLM Response Generation   |





## 📚 Why I’m Doing This

I’m building this project as part of my routine of my Daily Learnings  and my **#30DaysOfAIVoiceAgentshallenge.  
The aim is more than just writing code —  
it’s about learning to **integrate AI services**, improve **UI for humans**, and prepare myself for **real-world AI product development**.

If you’ve built something similar or have suggestions, drop me a message — I enjoy exchanging ideas with other builders. 🚀


💡 *Tomorrow… I aim to make response times even faster and experiment with extra voice options.*

