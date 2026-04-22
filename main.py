from fastapi import FastAPI, Request 
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates #for rendering the HTML templates
from exa_py import Exa
import os
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

#To run locally, you need to do 'uv run fastapi dev main.py' in console, then go to https://localhost:8000

load_dotenv()

# API keys needed for Exa and OpenAI, the AIs used for this app. Plug in your own keys here
#client = OpenAI(api_key="Your OpenAI API key here")
#exa = Exa(api_key="Your Exa API key here")

#can use these commands if you have an .env file setup
#client = OpenAI( api_key=os.getenv("OPENAI_API_KEY") )
#exa = Exa( api_key=os.getenv("EXA_API_KEY") )

class ChatRequest(BaseModel):
    message: str

def search_web(query: str):
    results = exa.search_and_contents(query, num_results=3)
    return [r.text[:300] for r in results.results]

app = FastAPI()
templates = Jinja2Templates(directory="templates")

#testing data for home page, can remove later
posts: list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

@app.get("/", include_in_schema=False)
@app.get("/posts", include_in_schema=False) #home page
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {'posts': posts})

@app.get("/api/posts") #shows the posts in json format, can be used for a frontend to pull from
def get_posts():
    return posts

@app.post("/api/chat")
def chat(req: ChatRequest):
    search_results = search_web(req.message)
    
    # Check if the message is asking for a list
    list_keywords = ["list", "top", "best", "recommend", "tactics", "tips", "ways", "methods", "examples", "types", "kinds"]
    is_list_query = any(keyword in req.message.lower() for keyword in list_keywords)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Only when the user explicitly asks for a list, format your response as a numbered list. For each item, provide: a brief name, then on the next line the description, strategy, and ROI. Format exactly like:\n1. Item Name\nDescription: [details]\nStrategy: [implementation steps]\nROI: [predicted return]\n\n2. Next Item\nDescription: [details]\n...etc\n\nOtherwise, respond normally without the list format."},
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": f"Here is context: {search_results}"}
        ]
    )
    
    content = response.choices[0].message.content
    
    # Only parse items if the query is asking for a list
    items = []
    if is_list_query:
        sections = content.split('\n\n')
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines or not lines[0]:
                continue
                
            # Extract item name from first line (e.g., "1. Item Name")
            first_line = lines[0]
            if '. ' not in first_line:
                continue
                
            name = first_line.split('. ', 1)[1].strip()
            
            # Extract description, strategy, and ROI from remaining lines
            description = ""
            strategy = ""
            roi = ""
            
            for line in lines[1:]:
                if line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                elif line.startswith("Strategy:"):
                    strategy = line.replace("Strategy:", "").strip()
                elif line.startswith("ROI:"):
                    roi = line.replace("ROI:", "").strip()
            
            if name:
                items.append({
                    "name": name,
                    "description": description,
                    "strategy": strategy,
                    "roi": roi
                })
    
    return {
        "response": content,
        "items": items
    }


    
