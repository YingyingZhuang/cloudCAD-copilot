# backend/test_backend.py
from onshape_client import OnshapeClient

# https://cad.onshape.com/documents/DID/w/WID/e/EID
DID = "f50e28300b77e78d0c047b45"
WID = "7bc9dfac7226c7a02984cc3a"
EID = "8b2be211d08ae2a28cf4a353" 

def test_connection():
    print(f" Connecting Onshape (Document: {DID})...")
    
    client = OnshapeClient()
    try:
        # Get holes from the specified Part Studio
        holes = client.analyze_geometry(DID, WID, EID)
        
        if holes:
            print("\nSuccessfully connected to Onshape and executed FeatureScript!")
            print(f"Found {len(holes)} features:")
            print(f"   Data: {holes}")
            print("------------------------------------------------")
        else:
            print("\nSuccessfully connected, but no holes detected (ID might be incorrect).")
            print("Please check if your EID belongs to the Part Studio containing the holes.")
            
    except Exception as e:
        print(f"\nTest failed: {e}")
        print("Please check if the Key in the .env file is correct.")

if __name__ == "__main__":
    test_connection()
