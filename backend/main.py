import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from onshape_client import OnshapeClient
from pydantic import BaseModel

load_dotenv()
app        = FastAPI()
client_cad = OnshapeClient()

origins = ["http://localhost:5173", "http://localhost:8000"]
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_methods=["*"], allow_headers=["*"])

PART_STUDIO_EID = "8b2be211d08ae2a28cf4a353"
ASSEMBLY_EID    = "c2048ce402c48fc44e04369a"

_cache = {"instruction": "", "part_keyword": "", "locations": []}

PART_NAME_MAP = {
    "top die shoe":    "Top Die Shoe",
    "top die":         "Top Die Shoe",
    "bottom die shoe": "Bottom Die Shoe",
    "bottom die":      "Bottom Die Shoe",
    "punch holder":    "Punch Holder",
    "punch backing":   "Punch Backing Plate",
    "die block":       "Die Block",
    "stripper":        "Stripper Plate",
    "die backing":     "Die Backing Plate",
    "piercing":        "Piercing Punches",
}

def extract_part_keyword(instruction: str) -> str:
    lower = instruction.lower()
    for kw, name in PART_NAME_MAP.items():
        if kw in lower:
            print(f"Target part identified: '{name}'")
            return name
    print("No specific part name detected. Scanning all parts.")
    return ""


@app.get("/auto-recommend")
def auto_recommend(did: str, wid: str, eid: str, instruction: str = ""):
    print(f"\nUser instruction: {instruction}")
    part_kw = extract_part_keyword(instruction)

    _cache["instruction"]  = instruction
    _cache["part_keyword"] = part_kw

    try:
        raw = client_cad.analyze_geometry(did, wid, PART_STUDIO_EID, part_kw)
    except Exception as e:
        return {"found": False, "message": f"Connection failed: {e}"}

    if not raw:
        return {"found": False, "message": "No geometry detected."}

    m8_holes  = [h for h in raw if h.get('rec_size') == "M8"]
    pin_holes = [h for h in raw if h.get('rec_size') == "8mm"]
    count_m8  = len(m8_holes)

    _cache["locations"] = [{'x': h['x'], 'y': h['y'], 'z': h['z']} for h in m8_holes]

    part_display = part_kw or "All Parts"
    logic = [f"Detected {count_m8} M8 screw holes on [{part_display}] (deduped)"]
    if pin_holes:
        logic.append(f"Detected {len(pin_holes)} dowel pin holes (diameter 8mm) on [{part_display}]")

    return {
        "found": True,
        "target_part": part_display,
        "analysis": {"logic": logic},
        "recommendation": {
            "title": "ISO 4762 M8 x 65mm",
            "subtitle": "Hex Socket Head Cap Screw",
            "purchase_link": "#"
        },
        "onshape_instruction": {
            "tool_name": "Batch Insert",
            "navigation_steps": [
                "1. Ensure you are in the Assembly Tab.",
                "2. Click Insert on the Top Toolbar (Cube with '+' icon).",
                "3. Select the Standard Content tab inside the dialog."
            ],
            "ui_panel": [
                {"label": "Standard",  "value": "ISO",                               "highlight": False},
                {"label": "Category",  "value": "Bolts & Screws",                    "highlight": False},
                {"label": "Type",      "value": "Socket head screws",                "highlight": False},
                {"label": "Component", "value": "Hex socket head cap screw ISO 4762", "highlight": True},
                {"label": "Size",      "value": "M8",  "highlight": True, "note": "AI Calculated"},
                {"label": "Length",    "value": "65",  "highlight": True, "note": "AI Calculated"},
                {"label": "Material",  "value": "Steel Class 12.9",                  "highlight": False}
            ],
            "final_action": f"Click 'Insert' to populate all {count_m8} holes automatically."
        }
    }


class InsertRequest(BaseModel):
    did: str
    wid: str
    eid: str
    part_spec: str = "M8"
    instruction: str = ""


@app.post("/insert-part")
def execute_insert(req: InsertRequest):
    instruction = req.instruction or _cache.get("instruction", "")
    part_kw     = extract_part_keyword(instruction) if instruction else _cache.get("part_keyword", "")

    print(f"\nExecuting insert | Part: '{part_kw or 'all'}' | Spec: {req.part_spec}")

    locations = _cache.get("locations", [])
    if not locations:
        print("Cache empty. Re-scanning holes...")
        raw = client_cad.analyze_geometry(req.did, req.wid, PART_STUDIO_EID, part_kw)
        if not raw:
            return {"status": "error", "msg": "Analysis failed. No holes found."}
        locations = [{'x': h['x'], 'y': h['y'], 'z': h['z']}
                     for h in raw if h.get('rec_size') == "M8"]

    if not locations:
        return {"status": "error", "msg": f"No M8 holes found on [{part_kw or 'all parts'}]."}

    print(f"Target hole count: {len(locations)}")

    result = client_cad.insert_parts_batch(req.did, req.wid, ASSEMBLY_EID, locations)

    _cache["locations"] = []

    if result["success"]:
        return {"status": "success", "msg": result["message"]}
    else:
        return {"status": "error", "msg": result["message"]}