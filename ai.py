from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
import json
import os


client = OpenAI(api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1")

def analyze_resume(resume_text, user_goal):
    prompt = f"""
You are a senior software engineer and hiring manager.
Evaluate the resume based on the user's goal.
User goal: "{user_goal}"

STRICT RULES:
- Extractonly relevent skills for this goal
- Remove irrelevant tools [excel for backend, etc]
- Identify real gaps
- Generate DIFFERENT base on goal

Return only JSON:
{{
"skills": [],
"missing_skills": [],
"roadmap": [],
"interview_questions": []
}}
Resume:
{resume_text}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You're a strict hiring manager."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content.strip()
        start = content.find("{")
        end = content.rfind("}")+1
        return json.loads(content[start:end])
    
    except Exception as e:
        return{
            "skills":[],
            "missing_skills":[],
            "roadmap":[],
            "interview_questions":[],
            "error": str(e)
        }
