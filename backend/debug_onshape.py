from onshape_client import OnshapeClient
from dotenv import load_dotenv
import os

# 1. 尝试加载环境变量
load_dotenv()
ak = os.getenv("ONSHAPE_ACCESS_KEY")
sk = os.getenv("ONSHAPE_SECRET_KEY")

print(f"🔑 Key Check: Access Key found? {'YES' if ak else 'NO'}")
if ak:
    print(f"🔑 Key Check: Access Key length: {len(ak)}")

# 2. 初始化客户端
try:
    client = OnshapeClient()
except Exception as e:
    print(f"❌ Client Init Failed: {e}")
    exit()

# 3. 填入你的真实 ID (Part Studio)
did = "f50e28300b77e78d0c047b45"
wid = "7bc9dfac7226c7a02984cc3a"
eid = "8b2be211d08ae2a28cf4a353" 

print(f"\n📡 Connecting to Onshape Part Studio ({eid})...")
result = client.analyze_geometry(did, wid, eid)

print("\n-------- RESULT --------")
print(result)
print("------------------------")
