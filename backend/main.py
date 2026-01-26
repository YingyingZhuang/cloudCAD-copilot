from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from collections import Counter
from onshape_client import OnshapeClient

app = FastAPI()
# Set up CORS middleware to allow requests from Onshape (https://cad.onshape.com) to access this computer(localhost).
origins = [
    "https://cad.onshape.com",  # allow Onshape access
    "http://localhost:3000",      # allow local development access
    "http://localhost:8000",      # allow Swagger UI access
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
#Simulated the cloud database
cloud_database = {
    "8.0": {
        "type":"Dowel Pin",
        "standard":"ISO 8734",
        # Mock Embedding of the First 4 Bits of a 768-Dimensional Vector
        "embedding": [0.12, -0.45, 0.88, 0.05], 
        "rag_context": "ISO 8734 Parallel Pins: Hardened steel (58-62 HRC). Tolerance h6. Used for precise alignment of mold plates.",
        "description": "Precision alignment pin. Requires H7 reamed hole.",
        "material": "Hardened Steel",
        "link": "https://www.mcmaster.com/dowel-pins/diameter~8mm/" 
    },
     "9.0": {
        "type": "Socket Head Cap Screw",
        "standard": "ISO 4762 M8",
        "embedding": [-0.67, 0.23, 0.11, -0.98],
        "rag_context": "ISO 4762 Socket Head Cap Screws: High tensile strength (>=1200 MPa). Requires clearance hole of 9mm for M8 size.",
        "description": "High-strength fastener. Clearance hole for M8.",
        "material": "Class 12.9 Steel",
        "link": "https://www.mcmaster.com/screws/thread-size~m8/"
    }
    }
client = OnshapeClient()
@app.get("/")
def read_root():
    return {"status": "CAD Copilot is ready online!"
}

@app.get("/auto-recommend")
def auto_recommend(did: str, wid: str, eid: str, instruction: str = ""):
    """
    Eample: User input: "Insert pin for Top Die Shoe"
    """
    print(f" Analyzing Document: {did}")
    print(f"User Instruction: {instruction}")

    # 1. Get a Part name with format: [{"part_name": "Top Die Shoe", "diameter": 8.0}, ...]
    raw_data = client.analyze_geometry(did, wid, eid)
    
    if not raw_data:
        return {"found": False, "message": "No geometry detected."}

    # 2. Semantic Filtering
    target_part_name = None
    filtered_diameters = []

    #Simple keyword matching logic (MVP)
    # It shoud use LLM extraction here, but for now we use simple string matching
    known_parts = set([item['part_name'] for item in raw_data])
    
    # check part name
    for part in known_parts:
        if part.lower() in instruction.lower():
            target_part_name = part
            break
    
    if target_part_name:
        print(f"Target Part Identified: {target_part_name}")
        # only keep the part's hole
        filtered_diameters = [d['diameter'] for d in raw_data if d['part_name'] == target_part_name]
    else:
        print("No specific part identified in instruction, scanning all.")
        # If the part name is not mentioned, then a full scan (Fallback) will be carried out.
        filtered_diameters = [d['diameter'] for d in raw_data]

    if not filtered_diameters:
        return {"found": False, "message": f"Part '{target_part_name}' found, but it has no holes."}

    # 3. Statistics & Recommendations
    most_common_dia = Counter(filtered_diameters).most_common(1)[0][0]
    print(f"Most common diameter on target: {most_common_dia}mm")
    
    key = str(round(most_common_dia, 1))
    item = cloud_database.get(key)
    
    if item:
        thickness = 35.0
        rec_length = thickness + 5 if "Pin" in item['type'] else round(thickness * 0.7)
        return {
            "found": True,
            "target_part": target_part_name if target_part_name else "All Parts",
            "detected_holes": len(filtered_diameters),
            "most_common_diameter": most_common_dia,
            "recommendation": {
                "part_name": f"{item['standard']} - {item['type']}",
                "spec": f"Size: {key}mm x {int(rec_length)}mm",
                "reasoning": f"Detected {most_common_dia}mm holes on {target_part_name or 'model'}.",
                "purchase_link": item['link']
            }
        }
    else:
        return {"found": False, "message": f"No standard part for {most_common_dia}mm holes."}
