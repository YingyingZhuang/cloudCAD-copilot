# CloudCAD-Copilot（prototype）: Context-Aware Standard Part Assistant

> An AI assistant (Demo) for automating standard part assembly on Onshape through natural language.
> Combines geometric analysis with engineering knowledge for intelligent recommendations.

## Overview
CloudCAD-Copilot is a "proof-of-concept" agent designed to bridge the gap between natural language commands and CAD geometric constraints. It leverages **LLMs for intent extraction** and **geometric clustering algorithms** to intelligently identify, select, and insert standard parts (e.g., ISO Screws) into the correct locations within an Onshape assembly.

> **Status:** Prototype Complete
> **Goal:** Eliminate manual lookups for ISO/ASME standard parts in mold design.

## Project Aims
- Hole Clustering: Implemented DBSCAN algorithm to group geometric features.
- Logic Engine: Built engineering reasoning engine based on ISO standards.
- Integration: Currently testing with real Onshape API (moving from mock data).
- UI: Streamlit interface for visualization.

## Core Capabilities(MVP)
This engineering judgment assistant goes beyond simple commands. It understands:
- Natural Language Input: Accepts instructions like insert screw for top die shoe and identifies the target part automatically.
- Contextual Targeting: Filters geometry by part name so only holes on the specified component are analysed.
- Feature Recognition: Distinguishes ø8mm dowel pin holes from ø9mm screw clearance holes using diameter thresholds.
- Standard Recommendation: Maps detected geometry to the correct ISO standard (It sets the rules: ISO 8734 for pins, ISO 4762 for screws).
- Engineering Calculation: Automatically calculates optimal fastener length based on plate thickness (e.g., Pin Length = Plate Thickness + 5mm).
- Batch Insert: Clones a seed fastener already in the assembly and inserts copies into all detected hole positions.
  
---
## Demo
![Demo Video](./assets/demo.gif)

*(Watch the full HD video demonstration with technical explanation [Here on YouTube](https://youtu.be/XqpCQ5_nefo))*

![Semantic Filtering Success](assets/demo_ui.png)
This is the CAD Copilot UI Panel, when you input the promote: insert screw for top die shoe, the AI detects 6 M8 screw holes and 4 dowel pin holes on the Top Die Shoe, recommends ISO 4762 M8 x 65mm, and triggers batch insert.
Then click "Insert" button, it will insert screws assembly.
![Semantic Filtering Success](assets/demo_assembly.png)

## Progress Log
### Phase 6: Batch Insert & Full Pipeline Closure
**Objective:** Close the loop from geometry detection to actual CAD modification.
* **Batch Insert Engine:**  scans the assembly for an existing M8 screw as a seed template, then clones and inserts it for each detected hole.
* **Assembly Scan:** The client queries GET /api/assemblies/.../ and searches rootAssembly.instances to locate the template part by name keywords (Hex, M8, ISO 4762).
* **Two-Step Insert Strategy:** Inserts via POST /instances, then attempts positional placement via POST /occurrences/transform.
* **Instruction Caching:** The backend caches the parsed part keyword and hole coordinates from auto-recommend so the subsequent insert-part call reuses them without re-scanning.
* **Deduplication:** Python-side deduplication groups cylindrical faces by coordinate (1e-4 m precision) to avoid double-counting top and bottom faces of the same hole.


### Phase 5: Generative AI Integration
**Objective:** Replace hard-coded logic with an LLM for intent understanding and dynamic reasoning.
* **OpenAI API:** Integrated GPT-3.5-turbo to process natural language instructions.
* **Prompt Engineering:** Designed a "Chain-of-Thought" prompt that forces the AI to output valid JSON and perform stack-up calculations (e.g., 35mm + 15mm + 15mm = 65mm).
* **Semantic Filtering:** Implemented a Python-side pre-processor to filter geometric data based on user keywords (e.g., "Top" filters for "Top Die Shoe"), solving the "Hallucination" problem of LLMs counting irrelevant holes.
* **Hybrid Architecture:** Established a "Python Eyes + AI Brain" workflow where Python handles precise measurement (Facts) and AI handles intent reasoning (Logic).

![Semantic Filtering Success](assets/demo_semantic_filtering.png)

### Phase 4: Full-Stack Integration & UI Guidance 
**Objective:** Upgrade from a data script to a user-facing application with "Hand-holding" guidance.
- **React Frontend:** Migrated to a modern web architecture using Vite + React.
- **Context-Aware Reasoning Engine:** The backend now performs real-time counting of features (e.g., "Detected 6x holes") and simulates stack-up analysis (Plate Thickness + Backing + Thread Depth) to calculate the precise Grip Length (e.g., 65mm).
- **Virtual Onshape Panel:** Developed a UI that mimics the Onshape "Standard Content" dialog. It highlights AI-calculated fields (like Length) to validate the engineer's choice.
- **Navigation Guidance:** Added step-by-step instructions (e.g., "Assembly Tab > Insert > Standard Content") to guide users to the correct tool location.
- 
### Phase 3: Intelligent Context Awareness 
- **Onshape API Integration:** Implemented a secure Python client (`backend/onshape_client.py`) with HMAC-SHA256 authentication to interact with the Onshape REST API.
- **Custom FeatureScript Protocol:** Designed a string-based protocol (`"PartName:::Diameter"`) to reliably extract geometry data, bypassing complex JSON nesting issues.
- **Semantic Filtering Engine:** The backend now parses natural language instructions (e.g., *"Insert pin for Top Die Shoe"*) and filters geometric features based on target part names.
 **Code:** [backend/main.py](backend/main.py)

### Phase 2: Geometric Analysis Kernel 
**Objective:** Enable Onshape to "see" and measure hole features natively then give the recommandation based on standards.

**Iteration 1: Basic Detection**
- Implemented B-Rep analysis to identify cylindrical topology.
- Achieved unit conversion awareness.

**Iteration 2: Edge-Side Inference (Current Version)**
- **Rule-Based RAG:** Embedded engineering logic directly into FeatureScript to map geometry to ISO standards.
- **Classification Engine:** Automatically categorizes features into "Dowel Pins" (<8.5mm) vs. "Screw Clearance" (>8.5mm).
- **Auto Calculating:** dynamic calculation of part lengths based on plate thickness (e.g., `Pin Length = Plate Thickness + 5mm`).

![Demo](assets/day2_featurescript_improvement.png)
*Figure: FeatureScript performing real-time inference, recommending ISO 8734 pins and ISO 4762 screws based on hole dimensions.*

📂 **Code:** [detectHoles.fs](featurescript/detectHoles.fs)

---

### Phase 1: API Connectivity & Data Retrieval
**Objective:** Establish secure communication with Onshape Cloud.
- Configured **REST API** client using Basic Auth (Access/Secret Keys).
- Successfully called `GET /api/assemblies` to retrieve the full hierarchical structure of a compound die.
- Parsed instance IDs (`elementId`, `partId`) needed for context-aware recommendations.

![Postman Test](assets/day1_postman_success.png)
*Figure: Validated API connection returning live assembly structure (Status 200 OK).*

📂 **Data Sample:** [assembly_data.json](api_tests/assembly_data.json)

## Future Roadmap
* **Spatial Transformation Matrix:** Enhance the FeatureScript to reliably extract 3D centroid coordinates of cylindrical faces.
* **Automated Mating:** Implement POST requests to the `/transforms` endpoint to automatically position and mate the batch-inserted fasteners directly into their respective target holes.
---

---

## Tech Stack
- **Frontend:** React, Vite, CSS3
- **Backend:** Python, FastAPI
- **Core Intelligence:** Onshape REST API, FeatureScript
- **AI Engine:** OpenAI API (GPT-4o)
- 
| Component | Description |
| :--- | :--- |
| Core Intelligence | Geometric clustering + Engineering rules, which analyzes spatial data. |
| Backend Logic | FastAPI server handling semantic filtering and context reasoning. |
| Frontend UI | React application providing a "Virtual Panel" and navigation steps. |
| Onshape Integration | Hybrid approach: Using FeatureScript for geometry extraction and REST API for data retrieval. |

---

## Project Structure

```text
CAD-Copilot/
├── backend/                # FastAPI Server (The Brain)
│   ├── main.py             # Context reasoning & API endpoints
│   ├── onshape_client.py   # Secure API wrapper (HMAC auth)
│   └── config.py           # Environment variables
├── frontend/               # React Application (The Face)
│   ├── src/App.jsx         # UI Logic & Virtual Panel component
│   └── src/App.css         # Styling
├── featurescript/          # Onshape Custom Features
│   └── detectHoles.fs      # Geometry extraction kernel
├── docs/                   # Documentation
│   └── README.md           # Project documentation
└── .env                    # Security keys (Excluded from Git)
```
---
##  How to Run

### Prerequisites
* Node.js & npm
* Python 3.x
* An Onshape account with API keys

### Step 1: Start the Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
#Create a .env file in the backend directory and add your API keys:
ONSHAPE_ACCESS_KEY=your_access_key
ONSHAPE_SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_key
#Start the server:
python3 -m uvicorn main:app --reload
```
### Step 2:Start the Frontend 
```bash
cd frontend
# Install dependencies (First time only)
npm install
# Run the Vite dev server
npm run dev
```
App runs on: http://localhost:5173
Type: "insert screw for top die" and click "Execute", then click "Insert" button.
## Known Limitations

- **Screw positioning:** Inserted screws currently appear at the assembly origin. Positional placement via POST /occurrences/transform is implemented but depends on Onshape returning a valid occurrence path, which the /instances endpoint does not currently provide in the response body.
- **Part name matching:** Keyword-based. The PART_NAME_MAP in main.py maps natural language input to exact part names in the target Onshape document.
- **Seed template required:** One M8 screw must be manually inserted into the assembly before running batch insert — the system clones this instance.
- **Document-specific IDs:** PART_STUDIO_EID and ASSEMBLY_EID in main.py are hardcoded to the development document and must be updated for a different Onshape document.
