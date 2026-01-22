from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import random #used to generate embedding vectors

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
@app.get("/")
def read_root():
    return {"status": "CAD Copilot is ready online!"
}

@app.get("/mcp/context")
def get_mcp_context(diameter: float):
    key = str(round(diameter,1))
    item = cloud_database.get(key)
    if item:
        return{
            "mcp_version": "1.0",
            "resource_type": "engineering_standard",
            "content": {
                "text": item["rag_context"],
                "embedding_preview": item["embedding"]
            }
        }
    else:
        return {"mcp_version": "1.0", "content": None}
#Core reason: Inserting standard parts
@app.get("/recommend")
def recommend(diameter: float, thinkness: float = 35.0):
    key = str(round(diameter,1))
    item = cloud_database.get(key)
    if item:
        if "Pin" in item["type"]:
           rec_length = thinkness + 5
        else:
           rec_length = round(thinkness*0.7)
        
        return {
            "found": True,
            "part_name": f"{item['standard']} - {item['type']}",
            "spec": f"Size: {key}mm x {int(rec_length)}mm",
            "material": item['material'],
            "reasoning": item['description'],
            "context_source": "Vector DB (Simulated)", # 强调数据来源
            "purchase_link": item['link']
        }
    else:
        return {
            "found": False,
            "message": "Standard part not found in knowledge base."
        }
