
import streamlit as st
import os
import google.generativeai as genai
import pdfplumber

# Placeholder for lazy-loaded modules
SentenceTransformer = None
util = None
pipeline = None
torch = None

# Model Constants
EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2' 
LLM_MODEL_NAME = 'MBZUAI/LaMini-Flan-T5-248M' 

class AICoach:
    def __init__(self):
        self.embedding_model = None
        self.llm_pipeline = None
        self.gemini_key = None
        self.device = "cpu" # Default until torch loads

    def set_gemini_key(self, key):
        self.gemini_key = key

    def _ensure_imports(self):
        """Lazy load heavy libraries."""
        global SentenceTransformer, util, pipeline, torch
        
        if torch is None:
            with st.spinner("Initializing AI Core (One-time setup)..."):
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                
        if SentenceTransformer is None:
            from sentence_transformers import SentenceTransformer, util
            
        if pipeline is None:
            from transformers import pipeline

    def load_embedding_model(self):
        """Loads embedding model (lightweight) separately."""
        self._ensure_imports()
        if self.embedding_model is None:
            try:
                self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=self.device)
            except Exception as e:
                st.error(f"Error loading Embeddings: {e}")

    def load_local_llm(self):
        """Loads local LLM only if needed."""
        self._ensure_imports()
        if self.llm_pipeline is None:
            try:
                st.toast("Downloading/Loading Local LLM... this may take a moment.")
                self.llm_pipeline = pipeline(
                    "text2text-generation", 
                    model=LLM_MODEL_NAME, 
                    device=0 if self.device == "cuda" else -1,
                    max_length=512
                )
            except Exception as e:
                st.error(f"Error loading Local LLM: {e}")

    def embed_text(self, text):
        self.load_embedding_model() # Ensure loaded
        if self.embedding_model:
            return self.embedding_model.encode(text, convert_to_tensor=True)
        return None

    def calculate_match(self, resume_text, job_description):
        self.load_embedding_model()
        if not self.embedding_model or not resume_text or not job_description:
            return 0
        resume_emb = self.embedding_model.encode(resume_text, convert_to_tensor=True)
        job_emb = self.embedding_model.encode(job_description, convert_to_tensor=True)
        score = util.cos_sim(resume_emb, job_emb).item()
        return round(score * 100, 1)

    def batch_rank_jobs(self, resume_text, jobs_list):
        """
        RAG Retrieval Step: Ranks a list of jobs against the resume.
        jobs_list: list of dicts or objects with 'title', 'company', 'location', 'source'
        """
        self.load_embedding_model()
        if not self.embedding_model:
            return []
            
        resume_emb = self.embedding_model.encode(resume_text, convert_to_tensor=True)
        scored_jobs = []
        
        # Create text representations for embedding
        job_texts = [f"{j.title} {j.company} {j.location} {j.source}" for j in jobs_list]
        job_embs = self.embedding_model.encode(job_texts, convert_to_tensor=True)
        
        # Calculate Cosine Similarity
        cosine_scores = util.cos_sim(resume_emb, job_embs)[0]
        
        # Pair up and sort
        for i, score in enumerate(cosine_scores):
            scored_jobs.append((jobs_list[i], score.item()))
            
        # Sort desc
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        return scored_jobs

    def _get_best_model(self):
        """Dynamically find the best available Gemini model."""
        try:
            # List all models
            available_models = [m.name for m in genai.list_models()]
            # Priority list (Updated for Speed/Stability)
            # Prioritize 1.5 Flash (Fastest, highest limits)
            priorities = [
                'models/gemini-1.5-flash',
                'models/gemini-1.5-pro',
                'models/gemini-3-flash-preview',
                'models/gemini-pro'
            ]
            
            for p in priorities:
                if p in available_models:
                    return genai.GenerativeModel(p)
            
            # Fallback: find any generating model
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    return genai.GenerativeModel(m.name)
            
            return None
        except Exception as e:
            st.error(f"Error listing models: {e}")
            return None

    def get_advice(self, resume_text, job_description):
        """Try Gemini first, then fall back to Local LLM"""
        
        prompt = f"""
        You are an expert AI Career Companion. Help the user land this job.
        
        **Target Job Description:**
        {job_description[:4000]}
        
        **User's Resume:**
        {resume_text[:4000]}
        
        **Task:**
        1. Identify the top 3 critical skills missing from the resume.
        2. Provide 1 specific, actionable piece of advice to improve their chances (e.g., a project idea, a certification, or a resume tweak).
        3. Rate their fit for this role on a scale of 1-10.
        
        **Tone:** Encouraging but realistic.
        Response:
        """

        # 1. Try Gemini
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                model = self._get_best_model()
                
                if model:
                    response = model.generate_content(prompt)
                    return f"**Gemini Career Analysis ({model.model_name}):**\n\n{response.text}"
                else:
                    return "Error: No supported Gemini models found for your API key."
                    
            except Exception as e:
                return f"Gemini API Error: {str(e)}. (Check your Key)"
        
        # 2. Fallback to Local
        self.load_local_llm()
        if self.llm_pipeline:
            output = self.llm_pipeline(prompt, max_length=512, do_sample=True, temperature=0.7)
            return f"**Local AI Analysis:**\n\n{output[0]['generated_text']}"
        
        return "No AI model available (Set Google_token in .env for Gemini)."

    def ask_coach(self, user_question, context=""):
        prompt = f"""
        You are a helpful AI Career Companion.
        
        **Context (Resume/Job Info):**
        {context[:5000]}
        
        **User Question:**
        {user_question}
        
        **Answer:**
        """
        
        # 1. Try Gemini
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                model = self._get_best_model()
                
                if model:
                    response = model.generate_content(prompt)
                    return f"{response.text}"
                else:
                    return "Error: No supported Gemini models found."

            except Exception as e:
                return f"Error: {e}"
        
        # 2. Fallback
        self.load_local_llm()
        if self.llm_pipeline:
             output = self.llm_pipeline(prompt, max_length=300)
             return f"{output[0]['generated_text']} *(Local AI)*"
        return "AI not available."

def extract_text_from_pdf(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

# Singleton instance
@st.cache_resource
def get_ai_coach():
    coach = AICoach()
    # We do NOT pre-load embeddings anymore to save startup time.
    # They will be loaded on first use.
    return coach
