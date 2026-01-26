# backend/onshape_client.py
import requests
import hmac
import hashlib
import base64
import random
import string
import json
import datetime
from config import Config

class OnshapeClient:
    def __init__(self):
        self.access_key = Config.ACCESS_KEY
        self.secret_key = Config.SECRET_KEY
        self.base_url = Config.BASE_URL
    
    def _make_nonce(self):
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(25))

    def _make_auth_header(self, method, path, query_string="", content_type="application/json"):
        nonce = self._make_nonce()
        date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        hmac_str = (method + "\n" + nonce + "\n" + date + "\n" +
                    content_type + "\n" + path + "\n" +
                    query_string + "\n").lower()
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode("utf-8"), hmac_str.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        auth_header = f"On {self.access_key}:HmacSHA256:{signature}"
        return {
            "Date": date, "On-Nonce": nonce, "Authorization": auth_header, "Content-Type": content_type
        }
    
    def analyze_geometry(self, did, wid, eid):
        
        method = "POST"
        path = f"/api/partstudios/d/{did}/w/{wid}/e/{eid}/featurescript"
        
        
        fs_code = r"""
        function(context is Context, queries) {
            var allBodies = qEverything(EntityType.BODY);
            var bodies = evaluateQuery(context, allBodies);
            var results = [];
            
            for (var body in bodies) {
                var partName = getProperty(context, {
                    "entity": body,
                    "propertyType": PropertyType.NAME
                });
                var bodyFaces = qOwnedByBody(body, EntityType.FACE);
                var faces = evaluateQuery(context, bodyFaces);
                
                for (var face in faces) {
                    var surf = evSurfaceDefinition(context, { "face" : face });
                    if (surf.surfaceType == SurfaceType.CYLINDER) {
                        var diameter = (surf.radius * 2) / millimeter;
                        if (diameter < 50) {
                            
                            results = append(results, partName ~ ":::" ~ diameter);
                        }
                    }
                }
            }
            return results; 
        }
        """
        
        payload = {"script": fs_code, "queries": []}
        headers = self._make_auth_header(method, path)
        try:
            response = requests.post(self.base_url + path, headers=headers, json=payload)
            if response.status_code == 200:
                resp_data = response.json()
                try:
                    
                    
                    raw_list = resp_data.get("result", {}).get("message", {}).get("value", [])
                    
                    clean_results = []
                    for item in raw_list:
                        
                        raw_str = item.get("message", {}).get("value")
                        
                        
                        if raw_str and isinstance(raw_str, str) and ":::" in raw_str:
                            parts = raw_str.split(":::")
                            if len(parts) >= 2:
                                clean_results.append({
                                    "part_name": parts[0],
                                    "diameter": round(float(parts[1]), 2)
                                })
                            
                    return clean_results
                except Exception as parse_e:
                    print(f"Parsing Error: {parse_e}")
                    
                    print(f"DEBUG Dump: {resp_data}")
                    return []
            else:
                print(f"API Error {response.status_code}")
                return []
        except Exception as e:
            print(f"Connection Error: {e}")
            return []
