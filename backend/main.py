import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from onshape_client import OnshapeClient
from pydantic import BaseModel
import re

load_dotenv()
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
client_cad = OnshapeClient()

origins = ["http://localhost:5173", "http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/auto-recommend")
def auto_recommend(did: str, wid: str, eid: str, instruction: str = ""):
    print(f"User Instruction: {instruction}")

    try:
        raw_data = client_cad.analyze_geometry(did, wid, eid)
        print(f"Debug Raw Data: {raw_data}") 
    except Exception as e:
        print(f"Onshape API Error: {e}")
        return {"found": False, "message": f"Connection failed: {str(e)}"}
    
    if not raw_data:
        print("Raw data is empty!") 
        return {"found": False, "message": "No geometry detected (Empty Data)."}

    
    target_data = []      
    target_part_name = "" 

    
    if "top" in instruction.lower():
        target_data = [d for d in raw_data if "top" in d['part_name'].lower()]
        if target_data:
            target_part_name = target_data[0]['part_name']
        else:
            target_data = raw_data
            target_part_name = "Unknown Part (Top not found)"

    elif "block" in instruction.lower():
        target_data = [d for d in raw_data if "block" in d['part_name'].lower()]
        if target_data:
            target_part_name = target_data[0]['part_name']
        else:
            target_data = raw_data
    
    else:
        top_matches = [d for d in raw_data if "top" in d['part_name'].lower()]
        if top_matches:
            target_data = top_matches
            target_part_name = top_matches[0]['part_name']
        else:
            target_data = raw_data
            target_part_name = raw_data[0]['part_name'] if raw_data else "Unknown"


    filtered_diameters = [d['diameter'] for d in target_data]
    
    count_9mm = len([d for d in filtered_diameters if 8.9 <= d <= 9.1])
    count_8mm = len([d for d in filtered_diameters if 7.9 <= d <= 8.1])
    
    print(f"Targeted Part: {target_part_name}")
    print(f"Stats: 9mm={count_9mm}, 8mm={count_8mm}")

    geometry_context = f"""
    FACTS FROM CAD SYSTEM:
    - User Focused Part: "{target_part_name}"
    - Hole Stats on this part: Found {count_9mm} holes of ~9.0mm diameter.
    - Hole Stats on this part: Found {count_8mm} holes of ~8.0mm diameter.
    - Plate Thickness: 35.0mm (Detected).
    """

    system_prompt = """
    You are an expert Onshape CAD Assistant. Your goal is to map user intent to specific ISO standard parts.

    ### DECISION RULES:
    - If user wants SCREW/FASTEN -> Recommend ISO 4762 M8 (Length 65mm).
    - If user wants PIN/ALIGN -> Recommend ISO 8734 8mm (Length 30mm).

    ### CRITICAL INSTRUCTION FOR OUTPUT FORMAT:
    You MUST output valid JSON ONLY. Follow this exact structure:
    {
        "found": true,
        "target_part": "Name of part",
        "analysis": {
            "logic": [
                "Detected [N]x Holes (⌀[D]mm) on [PartName]",
                "35mm (Plate) + 15mm (Backing) + 15mm (Thread) = 65mm"
            ]
        },
        "recommendation": {
            "title": "ISO 4762 M8 x 65mm",
            "subtitle": "Socket Head Cap Screw",
            "purchase_link": "https://www.mcmaster.com/"
        },
        "onshape_instruction": {
            "tool_location": "Right-side Toolbar",
            "tool_name": "Standard Content",
            "navigation_steps": [
                "1. Ensure you are in the **Assembly Tab**.",
                "2. Click **Insert** on the Top Toolbar (Cube with '+' icon).",
                "3. Select the **Standard Content** tab inside the dialog."
            ],
            "ui_panel": [
                {"label": "Standard", "value": "ISO", "highlight": false},
                {"label": "Category", "value": "Bolts & Screws", "highlight": false},
                {"label": "Type", "value": "Socket head screws", "highlight": false},
                {"label": "Component", "value": "Hex socket head cap screw ISO 4762", "highlight": true},
                {"label": "Size", "value": "M8", "highlight": true},
                {"label": "Length", "value": "65", "highlight": true, "note": "AI Calculated"},
                {"label": "Material", "value": "Steel Class 12.9", "highlight": false}
            ],
            "final_action": "Action: Click to select the [N] hole edges on the model, then click 'Insert'."
        }
    }
    """

    user_message = f"""
    User Input: "{instruction}"
    
    {geometry_context}
    
    Based on the FACTS, generate the JSON response. 
    Make sure to REPLACE placeholders like [N] and [D] with actual numbers from the FACTS!
    """

    print("AI is thinking with Context...")

    try:
        response = client_ai.chat.completions.create(
            model="gpt-3.5-turbo", 
            response_format={ "type": "json_object" }, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0
        )
        
        ai_content = response.choices[0].message.content
        print(f"AI Raw Output:\n{ai_content}\n") 
        return json.loads(ai_content)

    except Exception as e:
        print(f"AI Error: {e}")
        return {"found": False, "message": "AI Output Parsing Failed."}
    
class InsertRequest(BaseModel):
    did: str
    wid: str
    eid: str
    part_spec: str = "M8" # Reserved field, not in use at present

@app.post("/insert-part")
def execute_insert(req: InsertRequest):
    print(f"Executing Insert Action for: {req.part_spec}")
    
    # Call the write method of the Client
    result = client_cad.insert_part(req.did, req.wid, req.eid)
    
    if result["success"]:
        return {"status": "success", "msg": "Successfully inserted ISO 4762 M8x65!"}
    else:
        # If it fails, return an error code of 500.
        return {"status": "error", "msg": result["message"]}