# 🚀 Mini-RAG: Minimal Retrieval-Augmented Generation

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

A streamlined, high-performance RAG (Retrieval-Augmented Generation) implementation built with **FastAPI** and **Supabase**. This project serves as a professional baseline or educational template for building modern AI-powered question-answering systems.

---

## 🌟 Key Features

* **⚡ High Performance**: Lightweight FastAPI backend optimized for asynchronous processing.
* **👁️ Integrated OCR**: Advanced Optical Character Recognition for PDFs using AI-powered extraction.
* **🧠 Multi-LLM Orchestration**: Native integration with **OpenAI**, **Cohere**, **MistralAI**, and **Google Gemini**.
* **📂 Intelligent Document Processing**: Automated splitting and chunking of `.pdf` and `.txt` files.
* **🔎 Semantic Vector Search**: Powered by **Supabase Vector (pgvector)** for high-precision retrieval.
* **🪣 Multi-Bucket Storage**: Dynamic management of Supabase Storage buckets with automatic overflow handling (50MB limits).
* **🌊 Memory-Efficient Streaming**: Streaming file uploads to handle heavy assets without OOM risks.
* **🎨 Multi-language Support**: Configurable prompt templates for **Arabic** and **English**.
* **🔐 Development SSL**: Built-in self-signed certificate generation for secure local HTTPS testing.

---

## 🛠️ Technology Stack

| Category | Technology |
| :--- | :--- |
| **Framework** | ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi&logoColor=white) |
| **Database** | ![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) |
| **AI/LLM** | ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) |
| **Storage** | ![Supabase Storage](https://img.shields.io/badge/Supabase_Storage-3ECF8E?style=flat-square&logo=supabase&logoColor=white) |

---

## 🏗️ Architecture Overview

The system follows a clean, modular architecture designed for horizontal scalability:

```mermaid
graph TD
    User([User/Client]) -->|REST API| API[FastAPI Logic Layer]
    
    subgraph "Core Components"
        API --> DC[Data Controller: Upload & Stream]
        API --> NC[NLP Controller: Search & RAG]
        API --> PC[Process Controller: Chunking]
    end
    
    subgraph "Storage & Intelligence"
        DC -->|S3 Protocol| ST[Supabase Storage]
        NC -->|Embeddings| LLM[LLM Providers]
        NC -->|Vector Query| VDB[Supabase Vector]
        PC -->|Store Chunks| SDB[Supabase DB]
    end
```

---

## 🚀 Quick Start

### 1. Prerequisites

* Python 3.11+

* [Supabase Project](https://supabase.com/) (Free Tier works great!)

### 2. Installation

```bash
git clone https://github.com/AHMEDHANY146/MIni-RAG-APP-V1
conda create -n mini-rag python=3.11
conda activate mini-rag
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Update your credentials:

```env
SUPABASE_URL=your_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
OPENAI_API_KEY=your_openai_key
# Choose your providers
GENERATION_BACKEND=OPENAI
EMBEDDING_BACKEND=OPENAI
```

### 4. Run the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/data/upload/{project_id}` | Streaming file upload for processing. |
| `POST` | `/api/v1/data/process/{project_id}` | Chunk and index project files. |
| `POST` | `/api/v1/nlp/index/answer/{project_id}`| Query the RAG engine with natural language. |
| `GET` | `/api/v1/nlp/index/info/{project_id}` | Retrieve vector database health and info. |

---

## ❤️ Credits & Appreciation

This version is a refactored and production-ready evolution of the original project.
Special thanks to **[@bakrianoo](https://github.com/bakrianoo)** for the original inspiration and the incredible educational content that made this project possible.

## 📄 License

Licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
