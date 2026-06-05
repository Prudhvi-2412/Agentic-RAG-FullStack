# Render Deployment Guide: DocuMind AI

This guide explains how to deploy the DocuMind AI application on Render:
1. **FastAPI Backend** as a **Web Service**
2. **Vite React Frontend** as a **Static Site**

---

## 📦 Phase 1: Prepare Repository
Make sure your latest codebase is pushed to your GitHub repository (using `push_to_github.bat` or git commands).

---

## 🖥️ Phase 2: Deploy FastAPI Backend (Web Service)

1. Log in to your **[Render Dashboard](https://dashboard.render.com/)**.
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the service with the following settings:
   *   **Name**: `documind-api` (or any custom name)
   *   **Language**: `Python 3`
   *   **Root Directory**: `backend` (⚠️ **Crucial**: This tells Render to run commands inside the `/backend` subfolder)
   *   **Build Command**: `pip install -r requirements.txt`
   *   **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Advanced** and add the following **Environment Variables**:
   *   `GEMINI_API_KEY`: *Your Google AI Studio API Key*
   *   `PINECONE_API_KEY`: *Your Pinecone API Key*
   *   `PINECONE_INDEX_NAME`: `documind`
   *   `GEMINI_MODEL_NAME`: `gemini-2.5-flash`
6. Click **Create Web Service**.
7. **Copy the URL** Render assigns to your backend service once it builds successfully (e.g., `https://documind-api.onrender.com`).

---

## 🎨 Phase 3: Deploy React Frontend (Static Site)

1. Return to the **Render Dashboard**.
2. Click **New +** and select **Static Site**.
3. Connect the same GitHub repository.
4. Configure the service with the following settings:
   *   **Name**: `documind-ui` (or any custom name)
   *   **Root Directory**: `frontend` (⚠️ **Crucial**: Runs commands inside the `/frontend` subfolder)
   *   **Build Command**: `npm install && npm run build`
   *   **Publish Directory**: `dist`
5. Click **Advanced** and add the following **Environment Variables**:
   *   `VITE_BACKEND_URL`: *The URL of your deployed Backend Web Service* (e.g., `https://documind-api.onrender.com`)
6. Click **Create Static Site**.

---

## 🔍 Validation & Testing
*   Once both services are active (green indicator), open the URL of your **Static Site**.
*   Verify that your document library loads.
*   Upload a test PDF and verify that chunks are created and indexed successfully.
*   Ask a document-focused question to verify RAG streams are functioning on the production environment.
