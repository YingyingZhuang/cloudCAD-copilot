import os
from dotenv import load_dotenv

#Load the .env file in backend folder
load_dotenv()

class Config:
    ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY")
    SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY")
    #Ohsape base URL
    BASE_URL = "https://cad.onshape.com"

    # Check is key is exists, else raise error
    if not ACCESS_KEY or not SECRET_KEY:
        raise ValueError("Error: ONSHAPE_ACCESS_KEY or ONSHAPE_SECRET_KEY not found in .env file")