import { useState } from 'react'
import './App.css'

function App() {
  const [instruction, setInstruction] = useState("")
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)

  // IDs
  const DID = "f50e28300b77e78d0c047b45"
  const WID = "7bc9dfac7226c7a02984cc3a"
  const EID = "8b2be211d08ae2a28cf4a353"

  const handleSend = async () => {
    if (!instruction) return;
    setLoading(true);
    setResponse(null);

    try {
      const url = `http://localhost:8000/auto-recommend?did=${DID}&wid=${WID}&eid=${EID}&instruction=${encodeURIComponent(instruction)}`;
      const res = await fetch(url);
      const data = await res.json();
      setResponse(data);
    } catch (error) {
      setResponse({ found: false, message: "Backend error." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      padding: '30px', 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', 
      maxWidth: '900px', 
      margin: '0 auto',
      backgroundColor: '#1e1e1e', 
      minHeight: '100vh',
      color: '#fff'
    }}>
      {/* Header */}
      <div style={{marginBottom:'30px', borderBottom:'1px solid #333', paddingBottom:'20px'}}>
        <h1 style={{margin:0, fontSize:'28px', display:'flex', alignItems:'center', gap:'10px'}}>
          <span></span> CAD Copilot <span style={{fontSize:'12px', background:'#1d5bba', padding:'2px 8px', borderRadius:'4px'}}>DEMO</span>
        </h1>
        <p style={{color:'#888', margin:'5px 0 0 0'}}>Context-Aware Assembly Assistant</p>
      </div>
      
      {/* Input */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '40px' }}>
        <input 
          type="text" 
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Command: e.g. Insert screw for Top Die Shoe"
          style={{ 
            flex: 1, padding: '15px', borderRadius: '6px', border: '1px solid #444',
            fontSize: '16px', backgroundColor: '#2d2d2d', color: '#fff', outline:'none'
          }}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button 
          onClick={handleSend}
          disabled={loading}
          style={{ 
            padding: '0 30px', fontSize: '16px', cursor: 'pointer', 
            backgroundColor: '#1d5bba', color: 'white', border: 'none', borderRadius: '6px', fontWeight:'bold'
          }}
        >
          {loading ? "Computing..." : "Execute"}
        </button>
      </div>

      {/* Main Result Area */}
      {response && response.found && (
        <div style={{ display:'grid', gridTemplateColumns: '1fr 1.4fr', gap:'25px', animation: 'fadeIn 0.5s ease' }}>
          
          {/* Left Column: Logic */}
          <div style={{backgroundColor:'#2d2d2d', padding:'25px', borderRadius:'12px', border:'1px solid #444', height:'fit-content'}}>
            <div style={{color:'#888', textTransform:'uppercase', fontSize:'12px', fontWeight:'bold', marginBottom:'20px', letterSpacing:'1px', display:'flex', alignItems:'center', gap:'8px'}}>
              <span></span> Reasoning Engine
            </div>
            <ul style={{paddingLeft:'20px', margin:0, color:'#ddd', lineHeight:'1.8'}}>
              {response.analysis.logic.map((log, i) => (
                 <li key={i} style={{marginBottom:'10px'}}>
                   {log.includes('Grip Length') ? <strong style={{color:'#4caf50', fontSize:'1.1em'}}>{log}</strong> : log}
                 </li>
              ))}
            </ul>
            <div style={{marginTop:'30px', paddingTop:'20px', borderTop:'1px solid #444'}}>
              <div style={{fontSize:'14px', color:'#aaa', marginBottom:'5px'}}>Recommendation:</div>
              <div style={{fontSize:'20px', fontWeight:'bold', color:'#fff'}}>{response.recommendation.title}</div>
            </div>
          </div>

          {/* Right Column: UI Simulation */}
          <div style={{backgroundColor:'#fff', borderRadius:'12px', overflow:'hidden', color:'#333', boxShadow:'0 10px 30px rgba(0,0,0,0.3)'}}>
            
            {/* 1. Navigation Guide */}
            <div style={{backgroundColor:'#fff3cd', padding:'15px 20px', borderBottom:'1px solid #ffeeba'}}>
              <div style={{fontSize:'12px', fontWeight:'bold', color:'#856404', marginBottom:'8px', textTransform:'uppercase', display:'flex', justifyContent:'space-between'}}>
                <span>Navigation Guide</span>
                {response.onshape_instruction.help_url && (
                  <a href={response.onshape_instruction.help_url} target="_blank" style={{color:'#856404', textDecoration:'underline'}}>Help ?</a>
                )}
              </div>
              <div style={{fontSize:'14px', color:'#856404', lineHeight:'1.5'}}>
                 {response.onshape_instruction.navigation_steps.map((step, idx) => (
                   <div key={idx} dangerouslySetInnerHTML={{ __html: step }} style={{marginBottom:'4px'}}/>
                 ))}
              </div>
            </div>

            {/* 2. Tool Header */}
            <div style={{backgroundColor:'#f1f1f1', padding:'12px 20px', borderBottom:'1px solid #ddd', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
              <span style={{fontWeight:'bold', fontSize:'15px', color:'#333'}}>
                {response.onshape_instruction.tool_name}
              </span>
              <span style={{fontSize:'18px'}}></span>
            </div>

            {/* 3. Virtual Panel */}
            <div style={{padding:'20px 25px'}}>
              {response.onshape_instruction.ui_panel.map((field, idx) => (
                <div key={idx} style={{marginBottom:'12px', display:'flex', alignItems:'center'}}>
                  <div style={{width:'100px', fontSize:'13px', color:'#666', textAlign:'right', paddingRight:'15px'}}>
                    {field.label}:
                  </div>
                  <div style={{flex:1, position:'relative'}}>
                    <div style={{
                      padding:'8px 12px', 
                      borderRadius:'4px', 
                      border: field.highlight ? '2px solid #1d5bba' : '1px solid #ccc', 
                      backgroundColor: field.highlight ? '#e6f0ff' : '#fff',
                      fontSize:'14px',
                      fontWeight: field.highlight ? 'bold' : 'normal',
                      color:'#333'
                    }}>
                      {field.value}
                    </div>
                    {/* AI Note */}
                    {field.note && (
                      <div style={{
                        position:'absolute', right:'-8px', top:'-22px', 
                        backgroundColor:'#d32f2f', color:'white', fontSize:'10px', fontWeight:'bold',
                        padding:'2px 6px', borderRadius:'4px', whiteSpace:'nowrap', boxShadow:'0 2px 4px rgba(0,0,0,0.2)'
                      }}>
                        {field.note}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {/* 4. Final Action (New!) */}
              <div style={{marginTop:'25px', paddingTop:'15px', borderTop:'1px dashed #ddd', textAlign:'center'}}>
                <div style={{fontSize:'14px', fontWeight:'bold', color:'#d32f2f', marginBottom:'10px'}}>
                  {response.onshape_instruction.final_action}
                </div>
                <button style={{
                  backgroundColor:'#1d5bba', color:'white', border:'none', 
                  padding:'10px 40px', borderRadius:'6px', fontWeight:'bold', cursor:'default',
                  boxShadow:'0 4px 6px rgba(29, 91, 186, 0.3)'
                }}>
                  Insert
                </button>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}

export default App