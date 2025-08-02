# Dubai_Local_Explorer_AI_Chatbot
The **Dubai Local Explorer AI Chatbot** is a conversational assistant designed to help users plan their travel experience in Dubai.

# 📘 Dubai Local Explorer AI Chatbot – System Documentation

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-repo)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🧭 1. Project Overview

The **Dubai Local Explorer AI Chatbot** is a conversational assistant designed to help users plan their travel experience in Dubai. It leverages **large language models (LLMs)** via the OpenAI API to:

- Extract user intent and preferences from natural language  
- Recommend personalized experiences  
- Assist in booking  

The system is deployed via a **web interface using Flask**, with a clean, user-friendly chat UI.

---

## 🏗️ 2. System Design & Architecture

### 💡 Components

- **Frontend**: HTML, CSS, and JavaScript chat-style UI  
- **Backend**: Flask API handling user interaction and session state  
- **Chatbot Core** (`chatbot.py`): Performs logic and LLM-powered reasoning  
- **LLM Integration**: GPT-4 or GPT-3.5 for structured preference extraction and conversational responses  
- **Experience Data Layer**: Currently a static list of Dubai activities, with easy integration potential for APIs

### 🔁 Architecture Flow


---

## ⚙️ 3. Functionalities & Features

- Accepts free-form user input
- Extracts structured preferences:
  - Interests
  - Budget
  - Travel duration
  - Group type
- Recommends suitable Dubai experiences
- Confirmation and clarification dialogues
- Modular experience database
- Web UI with auto-scroll, typing indicator, etc.

---

## 🧠 4. Core Logic (`chatbot.py`)

The system follows a **layered reasoning pipeline**, including:

### 📤 `extract_information()`
Extracts structured data (interests, budget, etc.) using prompt engineering with OpenAI.

### 🧾 `extract_dictionary_from_string()`
Converts LLM output into a dictionary using `ast.literal_eval`.

### 📌 `match_experiences_to_profile()`
Filters and ranks experiences based on:
- Interest overlap
- Budget match
- Group compatibility
- Duration

### 🎯 `product_recommendation_layer()`
Converts top results into human-friendly recommendations with rationale.

---

## 🧱 Architecture Layers Explained
User → Web Interface → Flask → Chatbot Core → OpenAI API → Response → Flask → Web UI

### 1. **Intent Clarity Layer**
Prompts users to clarify vague input.

> Input: “I want to do something fun.”  
> Output: “Are you looking for adventure, relaxation, or something cultural?”

### 2. **Intent Confirmation Layer**
Confirms extracted preferences before proceeding.

```json
{
  "interests": ["food", "beaches"],
  "budget_aed": 500,
  "duration_days": 2,
  "group_type": "family"
}

3. Product Mapping Layer
Matches preferences with database items using weighted scoring.

4. Product Information Extraction Layer
Gathers metadata from selected experiences for enhanced recommendations.

5. Product Recommendation Layer
Presents results in user-friendly text with justification.

6. (Optional) Moderation Layer
Filters unsafe input using OpenAI Moderation API.

User Input -> Moderation -> Clarity -> Extraction -> Confirmation -> Mapping -> Info Extraction -> Recommendation -> Output

5. User Journey – Example
User Input:

"I'm visiting Dubai with my friends for 3 days. We like adventure and beaches. Budget is 700 AED."

Bot Flow:

Extracts:
{
  "interests": ["adventure", "beaches"],
  "budget_aed": 700,
  "duration_days": 3,
  "group_type": "friends"
}

Matches: Desert Safari, JBR Beach, etc.

Presents ranked suggestions with explanations

Awaits feedback or booking confirmation

7. Deployment Guide
✅ 1. Install Requirements

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Set OpenAI API Key

export OPENAI_API_KEY=your-api-key

Run Locally

python app.py
Navigate to http://localhost:5000

Deploy Online (Optional)
Supported Platforms:

Render

Heroku

Replit

Heroku Example:

makefile
Copy
Edit
Procfile:
web: gunicorn app:app

8. Limitations & Enhancements
🔻 Current Limitations
Static experience database

No persistent memory

No authentication

Occasional LLM hallucinations

🚀 Future Enhancements
Real-time Dubai API integration

Add user profiles, login, and history

WhatsApp, PDF, or map-based itineraries

Feedback loop for smarter recommendations
