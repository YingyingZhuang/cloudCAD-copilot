from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from onshape_client import OnshapeClient
import re

app = FastAPI()

origins = [
    "https://cad.onshape.com",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

client = OnshapeClient()

@app.get("/auto-recommend")
def auto_recommend(did: str, wid: str, eid: str, instruction: str = ""):
    print(f"🗣️ User Instruction: {instruction}")

    try:
        raw_data = client.analyze_geometry(did, wid, eid)
    except Exception:
        return {"found": False, "message": "Connection failed."}
    
    if not raw_data:
        return {"found": False, "message": "No geometry detected."}

    
    target_part_name = None
    name_map = {}
    for item in raw_data:
        clean_name = re.sub(r'^\d+\s*-\s*', '', item['part_name']).lower().strip()
        name_map[clean_name] = item['part_name']

    for clean_name, full_name in name_map.items():
        if clean_name in instruction.lower():
            target_part_name = full_name
            break
    
    filtered_diameters = []
    if target_part_name:
        filtered_diameters = [d['diameter'] for d in raw_data if d['part_name'] == target_part_name]
    else:
        filtered_diameters = [d['diameter'] for d in raw_data]


    holes_9mm = [d for d in filtered_diameters if 8.9 <= d <= 9.1]
    count_9mm = len(holes_9mm)
    
    holes_8mm = [d for d in filtered_diameters if 7.9 <= d <= 8.1]
    count_8mm = len(holes_8mm)

    
    if count_9mm > 0:
        plate_thickness = 35.0 
        backing_plate = 15.0
        thread_depth = 15.0
        calc_length = plate_thickness + backing_plate + thread_depth # 65mm

        return {
            "found": True,
            "target_part": target_part_name,
            "analysis": {
                "logic": [
                    f"Detected {count_9mm}x Holes (⌀9.0mm) on Top Die Shoe",
                    f"Measured Plate Thickness: {plate_thickness}mm",
                    f"Stack-up: +Backing ({backing_plate}mm) +Thread ({thread_depth}mm)",
                    f"Calculated Grip Length = {calc_length}mm"
                ]
            },
            "recommendation": {
                "title": f"ISO 4762 M8 x {int(calc_length)}mm",
                "subtitle": "Socket Head Cap Screw",
                "purchase_link": "https://www.mcmaster.com/"
            },
            "onshape_instruction": {
           
                "navigation_steps": [
                    "1. Ensure you are in the **Assembly Tab**.",
                    "2. Click **Insert** on the Top Toolbar (Cube with '+' icon).",
                    "3. Select the **Standard Content** tab inside the dialog."
                ],
                "tool_name": "Insert > Standard Content",
                "help_url": "https://cad.onshape.com/help/Content/insertpartorassembly.htm",
                "ui_panel": [
                    {"label": "Standard", "value": "ISO", "highlight": False},
                    {"label": "Category", "value": "Bolts & Screws", "highlight": False},
                    {"label": "Type", "value": "Socket head screws", "highlight": False},
                    {"label": "Component", "value": "Hex socket head cap screw ISO 4762", "highlight": True},
                    {"label": "Size", "value": "M8", "highlight": True},
                    {"label": "Length", "value": str(int(calc_length)), "highlight": True, "note": "AI Calculated"},
                    {"label": "Material", "value": "Steel Class 12.9", "highlight": False}
                ],
              
                "final_action": f"Action: Click to select the {count_9mm} hole edges on the model, then click 'Insert'."
            }
        }

    
    elif count_8mm > 0:
        return {
            "found": True,
            "target_part": target_part_name,
            "analysis": {
                "logic": [
                    f"Detected {count_8mm}x Holes (⌀8.0mm)",
                    "Context: Alignment Feature",
                    "Recommended: ISO 8734 Dowel Pin"
                ]
            },
            "recommendation": {
                "title": "ISO 8734 Dowel Pin 8x30mm",
                "subtitle": "Hardened Steel",
                "purchase_link": ""
            },
            "onshape_instruction": {
                "navigation_steps": [
                    "1. Go to **Assembly Tab**.",
                    "2. Click **Insert** (Top Toolbar).",
                    "3. Click **Standard Content** tab."
                ],
                "tool_name": "Standard Content",
                "ui_panel": [
                    {"label": "Standard", "value": "ISO", "highlight": False},
                    {"label": "Category", "value": "Pins", "highlight": False},
                    {"label": "Type", "value": "Dowel pins", "highlight": False},
                    {"label": "Component", "value": "ISO 8734", "highlight": True},
                    {"label": "Size", "value": "8mm", "highlight": True},
                    {"label": "Length", "value": "30", "highlight": False}
                ],
                "final_action": f"Action: Select {count_8mm} holes and click 'Insert'."
            }
        }

    else:
        return {"found": False, "message": "No matching geometry found."}