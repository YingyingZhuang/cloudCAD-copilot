import os
import base64
import hmac
import hashlib
import random
import string
import datetime
import requests

class OnshapeClient:
    def __init__(self):
        self.base_url = "https://cad.onshape.com"
        self.access_key = os.getenv("ONSHAPE_ACCESS_KEY")
        self.secret_key = os.getenv("ONSHAPE_SECRET_KEY")

    def _make_headers(self, method, path, query={}, headers={}):
        sk    = self.secret_key.encode('utf-8')
        nonce = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(25))
        date  = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        qs    = '&'.join(f"{k}={v}" for k, v in query.items())
        msg   = (method.upper() + '\n' + nonce + '\n' + date + '\n' +
                 headers.get('Content-Type', 'application/json') + '\n' +
                 path + '\n' + qs + '\n').lower().encode('utf-8')
        sig   = base64.b64encode(hmac.new(sk, msg, digestmod=hashlib.sha256).digest()).decode()
        return {
            'On-Nonce': nonce,
            'Date': date,
            'Authorization': f"On {self.access_key}:HmacSHA256:{sig}",
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.onshape.v1+json'
        }

    def _parse_fs_value(self, data):
        if not isinstance(data, dict):
            return data
        t = data.get('typeName')
        if t == 'BTFSValueMap':
            result, entries = {}, data.get('message', {}).get('value', [])
            for e in entries:
                if e.get('typeName') == 'BTFSValueMapEntry':
                    result[self._parse_fs_value(e['message']['key'])] = \
                           self._parse_fs_value(e['message']['value'])
            return result
        if t in ('BTFSValueString', 'BTFSValueNumber', 'BTFSValueBoolean'):
            return data.get('message', {}).get('value')
        if t == 'BTFSValueArray':
            return [self._parse_fs_value(i) for i in data.get('message', {}).get('value', [])]
        return data

    def analyze_geometry(self, did, wid, eid, target_part_keyword=""):
        path = f"/api/partstudios/d/{did}/w/{wid}/e/{eid}/featurescript"
        kw   = target_part_keyword.replace('"', '\\"')
        script = f"""
        function(context is Context, queries) {{
            var allFaces = qEverything(EntityType.FACE);
            var faces    = evaluateQuery(context, allFaces);
            var results  = [];
            var targetKW = "{kw}";

            for (var i = 0; i < size(faces); i += 1) {{
                var face = faces[i];
                try {{
                    var sd = evSurfaceDefinition(context, {{ "face": face }});
                    if (sd.surfaceType != SurfaceType.CYLINDER) {{ continue; }}

                    var dia = round(sd.radius.value * 2 * 1e5) / 100.0;
                    if (dia >= 50.0) {{ continue; }}

                    var ownerBody = qOwnerBody(face);
                    var pname = "Unknown";
                    try {{ pname = getProperty(context, {{"entity": ownerBody,
                                "propertyType": PropertyType.PART_NUMBER}}); }} catch(e) {{}}
                    if (pname == undefined || pname == "") {{
                        try {{ pname = getProperty(context, {{"entity": ownerBody,
                                    "propertyType": PropertyType.NAME}}); }} catch(e) {{}}
                    }}
                    if (targetKW != "" && indexOf(pname, targetKW) == -1) {{ continue; }}

                    var cs = sd.coordSystem;
                    var cx = cs.origin[0] / meter;
                    var cy = cs.origin[1] / meter;
                    var cz = cs.origin[2] / meter;

                    var recSize = dia < 8.5 ? "8mm" : "M8";

                    results = append(results, {{
                        "diameter": dia, "part_name": pname,
                        "rec_size": recSize,
                        "x": cx, "y": cy, "z": cz
                    }});
                }} catch(e) {{
                    println("ERR face " ~ i ~ ": " ~ e);
                    continue;
                }}
            }}
            return results;
        }}
        """
        hdrs = self._make_headers("POST", path)
        try:
            print(f"Running FeatureScript analysis (filter: '{target_part_keyword or 'all'}')...")
            r = requests.post(f"{self.base_url}{path}", headers=hdrs,
                              json={"script": script, "queries": []})
            if r.status_code != 200:
                print(f"API error: {r.status_code} - {r.text[:200]}")
                return None

            data = r.json()
            if 'result' in data and data['result'].get('console'):
                print(f"FeatureScript log:\n{data['result']['console']}")
            if 'result' not in data or 'message' not in data['result']:
                print(f"Unexpected JSON structure: {list(data.keys())}")
                return None

            raw = [self._parse_fs_value(item) for item in data['result']['message']['value']]

            seen, clean = set(), []
            for h in raw:
                key = (round(h.get('x', 0) * 1e4),
                       round(h.get('y', 0) * 1e4),
                       round(h.get('z', 0) * 1e4),
                       h.get('rec_size', ''))
                if key not in seen:
                    seen.add(key)
                    clean.append(h)

            print(f"Analysis complete: {len(raw)} faces -> {len(clean)} unique holes after dedup")
            return clean
        except Exception as e:
            print(f"Analysis error: {e}")
            return None

    def find_template_in_assembly(self, did, wid, eid, keywords):
        print(f"Searching assembly for template part matching: {keywords}")
        path = f"/api/assemblies/d/{did}/w/{wid}/e/{eid}"
        hdrs = self._make_headers("GET", path)
        try:
            r = requests.get(f"{self.base_url}{path}", headers=hdrs)
            if r.status_code == 200:
                for inst in r.json().get('rootAssembly', {}).get('instances', []):
                    name = inst.get('name', '')
                    if any(k.lower() in name.lower() for k in keywords):
                        print(f"Template found: {name}")
                        src = {
                            "documentId": inst['documentId'],
                            "elementId":  inst['elementId'],
                            "partId":     inst['partId'],
                            "isAssembly": False,
                            "isWholePartStudio": False
                        }
                        vid = inst.get('documentVersion') or inst.get('documentVersionId')
                        if vid:
                            src['versionId'] = vid
                        else:
                            src['workspaceId'] = wid
                        if 'configuration' in inst:
                            src['configuration'] = inst['configuration']
                        return src, name
        except Exception as e:
            print(f"Error searching assembly: {e}")
        return None, None

    def _get_instance_ids(self, did, wid, eid):
        path = f"/api/assemblies/d/{did}/w/{wid}/e/{eid}"
        hdrs = self._make_headers("GET", path)
        try:
            r = requests.get(f"{self.base_url}{path}", headers=hdrs)
            if r.status_code == 200:
                instances = r.json().get('rootAssembly', {}).get('instances', [])
                return {inst.get('id') for inst in instances if inst.get('id')}
        except Exception as e:
            print(f"Error fetching instance list: {e}")
        return set()

    def _apply_transform(self, did, wid, eid, instance_id, x, y, z):
        path = f"/api/assemblies/d/{did}/w/{wid}/e/{eid}/occurrences/transform"
        hdrs = self._make_headers("POST", path)
        payload = {
            "occurrences": [{"path": [instance_id]}],
            "transform": [
                1, 0, 0, x,
                0, 1, 0, y,
                0, 0, 1, z,
                0, 0, 0, 1
            ],
            "isRelative": False
        }
        r = requests.post(f"{self.base_url}{path}", headers=hdrs, json=payload)
        return r.status_code == 200

    def insert_parts_batch(self, target_did, target_wid, target_eid, locations):
        template_def, template_name = self.find_template_in_assembly(
            target_did, target_wid, target_eid, ["Hex", "M8", "ISO 4762"])
        if not template_def:
            return {"success": False,
                    "message": "No M8 screw template found in assembly. Please insert one manually first."}

        insert_payload = {k: v for k, v in template_def.items() if k != 'position'}
        insert_path    = (f"/api/assemblies/d/{target_did}/w/{target_wid}"
                          f"/e/{target_eid}/instances")

        ok, fail = 0, 0
        print(f"Starting batch insert of {len(locations)} screws...")

        for i, loc in enumerate(locations):
            x, y, z = loc['x'], loc['y'], loc['z']
            try:
                ids_before  = self._get_instance_ids(target_did, target_wid, target_eid)
                hdrs        = self._make_headers("POST", insert_path)
                r           = requests.post(f"{self.base_url}{insert_path}",
                                            headers=hdrs, json=insert_payload)
                if r.status_code not in (200, 201):
                    print(f"  [{i+1}] Insert failed: {r.status_code} - {r.text[:150]}")
                    fail += 1
                    continue

                ids_after   = self._get_instance_ids(target_did, target_wid, target_eid)
                new_ids     = ids_after - ids_before
                instance_id = next(iter(new_ids)) if new_ids else None

                if not instance_id:
                    print(f"  [{i+1}] Inserted but could not retrieve instance ID. Screw placed at origin.")
                    ok += 1
                    continue

                moved = self._apply_transform(target_did, target_wid, target_eid, instance_id, x, y, z)
                if moved:
                    print(f"  [{i+1}] Placed at ({x*1e3:.1f}, {y*1e3:.1f}, {z*1e3:.1f}) mm")
                else:
                    print(f"  [{i+1}] Inserted but transform failed. Screw placed at origin.")
                ok += 1

            except Exception as e:
                print(f"  [{i+1}] Error: {e}")
                fail += 1

        return {"success": True,
                "message": f"Done. Inserted {ok} screws successfully, {fail} failed."}