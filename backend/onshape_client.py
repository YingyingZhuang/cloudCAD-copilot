import os
import base64
import hmac
import hashlib
import random
import string
import datetime
import requests
import json

class OnshapeClient:
    def __init__(self):
        self.base_url = "https://cad.onshape.com"
        self.access_key = os.getenv("ONSHAPE_ACCESS_KEY")
        self.secret_key = os.getenv("ONSHAPE_SECRET_KEY")

    def _make_headers(self, method, path, query={}, headers={}):
        access_key = self.access_key.encode('utf-8')
        secret_key = self.secret_key.encode('utf-8')
        
        nonce = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(25))
        auth_date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        qs = '&'.join(f"{k}={v}" for k, v in query.items())
    
        payload = (
            method.upper() + '\n' +
            nonce + '\n' +
            auth_date + '\n' +
            headers.get('Content-Type', 'application/json') + '\n' +
            path + '\n' +
            qs + '\n'
        ).lower().encode('utf-8')

        signature = base64.b64encode(hmac.new(secret_key, payload, digestmod=hashlib.sha256).digest()).decode('utf-8')
        
        auth_header = f"On {self.access_key}:HmacSHA256:{signature}"
        
        return {
            'On-Nonce': nonce,
            'Date': auth_date,
            'Authorization': auth_header,
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.onshape.v1+json'
        }

    # 🟢 数据清洗函数
    def _parse_fs_value(self, data):
        if not isinstance(data, dict): return data
        type_name = data.get('typeName')
        if type_name == 'BTFSValueMap':
            result = {}
            entries = data.get('message', {}).get('value', [])
            for entry in entries:
                if entry.get('typeName') == 'BTFSValueMapEntry':
                    k = self._parse_fs_value(entry['message']['key'])
                    v = self._parse_fs_value(entry['message']['value'])
                    result[k] = v
            return result
        if type_name in ['BTFSValueString', 'BTFSValueNumber', 'BTFSValueBoolean']:
            return data.get('message', {}).get('value')
        if type_name == 'BTFSValueArray':
             return [self._parse_fs_value(i) for i in data.get('message', {}).get('value', [])]
        return data

    def analyze_geometry(self, did, wid, eid):
        """ [GET] Analyze geometry """
        path = f"/api/partstudios/d/{did}/w/{wid}/e/{eid}/featurescript"
        script = r"""
        function(context is Context, queries) {
            var allFaces = qEverything(EntityType.FACE);
            var faces = evaluateQuery(context, allFaces);
            var results = [];
            var plateThickness = 35.0;
            for (var i = 0; i < size(faces); i += 1) {
                var face = faces[i];
                try {
                    var surfaceDef = evSurfaceDefinition(context, { "face" : face });
                    if (surfaceDef.surfaceType == SurfaceType.CYLINDER) {
                        var diameterMM = surfaceDef.radius.value * 2 * 1000;
                        var finalDia = round(diameterMM * 100) / 100;
                        if (finalDia < 50.0) {
                            var ownerBody = qOwnerBody(face);
                            var partName = "Unknown";
                            try { partName = getProperty(context, { "entity": ownerBody, "propertyType": PropertyType.PART_NUMBER }); } catch(e) {}
                            if (partName == undefined || partName == "" || partName == "Unknown") {
                                 try { partName = getProperty(context, { "entity": ownerBody, "propertyType": PropertyType.NAME }); } catch(e) {}
                            }
                            var holeType = "Screw Clearance";
                            var isoStandard = "ISO 4762";
                            var recSize = "";
                            var recLength = 0;
                            if (finalDia < 8.5) {
                                holeType = "Dowel Pin"; isoStandard = "ISO 8734"; recSize = (round(finalDia * 10) / 10) ~ "mm"; recLength = plateThickness + 5;
                            } else {
                                holeType = "Screw Clearance"; isoStandard = "ISO 4762"; var mSize = round(finalDia - 1); recSize = "M" ~ mSize; recLength = round(plateThickness * 0.7);
                            }
                            results = append(results, { "diameter": finalDia, "part_name": partName, "hole_type": holeType, "iso_standard": isoStandard, "recommended_size": recSize, "recommended_length": recLength });
                        }
                    }
                } catch(e) { continue; }
            }
            return results;
        }
        """
        headers = self._make_headers("POST", path)
        try:
            response = requests.post(f"{self.base_url}{path}", headers=headers, json={"script": script, "queries": []})
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'message' in data['result']:
                    return [self._parse_fs_value(item) for item in data['result']['message']['value']]
            return None
        except Exception: return None

    def insert_part(self, target_did, target_wid, target_eid):
        """ 
        [POST] 智能插入：自动从当前零件库中寻找一个小零件作为 '螺丝替身' 插入。
        解决 404 问题，确保证明系统写入能力。
        """
        # 源头依然是你自己的 Part Studio (保证不 404)
        src_eid = "8b2be211d08ae2a28cf4a353" 
        
        # --- 第一步：侦察 (Get Parts) ---
        print(f"🕵️ Scanning source studio for a suitable part...")
        parts_path = f"/api/parts/d/{target_did}/w/{target_wid}/e/{src_eid}"
        headers_get = self._make_headers("GET", parts_path)
        
        part_id = None
        part_name = "Unknown Part"
        
        try:
            resp = requests.get(f"{self.base_url}{parts_path}", headers=headers_get)
            if resp.status_code == 200:
                parts = resp.json()
                # 🎯 策略：优先寻找名字里带 "Cutter" 或 "Pin" 的小零件
                # 如果找不到，就取列表里的第一个零件作为备选
                candidates = [p for p in parts if "Cutter" in p['name'] or "Pin" in p['name']]
                
                if candidates:
                    target_part = candidates[0]
                    print(f"✅ Found smart match: {target_part['name']}")
                elif parts:
                    target_part = parts[0]
                    print(f"⚠️ No screw-like part found, using first available: {target_part['name']}")
                else:
                    return {"success": False, "message": "Source Part Studio is empty!"}
                
                part_id = target_part['partId']
                part_name = target_part['name']
                
            else:
                return {"success": False, "message": f"Scan failed: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

        if not part_id:
            return {"success": False, "message": "Could not find a valid Part ID."}

        # --- 第二步：精准打击 (Insert Specific Part) ---
        insert_path = f"/api/assemblies/d/{target_did}/w/{target_wid}/e/{target_eid}/instances"
        
        payload = {
            "documentId": target_did,
            "elementId": src_eid,
            "workspaceId": target_wid,
            "isAssembly": False,
            "isWholePartStudio": False, # 🔴 关键：不复制整个工作室
            "partId": part_id           # 🟢 关键：只插入我们找到的那个零件
        }
        
        headers_post = self._make_headers("POST", insert_path)
        
        print(f"📡 Inserting part: {part_name}...")
        try:
            response = requests.post(f"{self.base_url}{insert_path}", headers=headers_post, json=payload)
            
            if response.status_code == 200:
                # 成功！告诉前端我们插了什么
                return {"success": True, "message": f"Success! Inserted '{part_name}' as M8 Screw placeholder."}
            else:
                return {"success": False, "message": f"Insert Failed: {response.text}"}
                
        except Exception as e:
            return {"success": False, "message": str(e)}