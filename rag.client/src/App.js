import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles } from "lucide-react";

function App() {
  const [projects, setProjects] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedProject, setSelectedProject] = useState("");
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful technical assistant.");
  const chatEndRef = useRef(null);
  const [sources, setSources] = useState([]);

  // --- API Calls ---
  
  const fetchProjects = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/projects');
      setProjects(res.data.projects);
      if (res.data.projects.length > 0 && !selectedProject) setSelectedProject(res.data.projects[0]);
    } catch (err) { console.error("Error fetching projects", err); }
  };

  const fetchModels = async () => {
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/models`);
      setAvailableModels(res.data);
      // Set first available/configured model as default
      if (res.data.length > 0 && !selectedModel) {
        const defaultModel = res.data.find(m => m.configured) || res.data[0];
        setSelectedModel(defaultModel.id);
      }
    } catch (err) { console.error("Error fetching models", err); }
  };

  const fetchSources = async () => {
    if (!selectedProject) return;
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/projects/${selectedProject}/sources`);
      setSources(res.data.sources || []);
    } catch (err) { console.error("Error fetching sources", err); }
  };

  // שליפת היסטוריית השיחות מ-MongoDB
  const fetchChatHistory = async () => {
    if (!selectedProject) return;
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/chat/history?project=${selectedProject}&user_id=user_1`);
      setChatHistory(res.data.history || []);
    } catch (err) {
      console.error("Error fetching chat history from MongoDB", err);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchModels();
  }, []);

  // רענון המקורות וההיסטוריה ממונגו ברגע שמחליפים פרויקט
  useEffect(() => {
    fetchSources();
    fetchChatHistory();
  }, [selectedProject]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // --- Actions ---

  const uploadFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    try {
      await axios.post(`http://127.0.0.1:8000/api/files/upload?project=${selectedProject}`, formData);
      fetchSources();
      alert("File uploaded successfully");
    } catch (err) { alert("Error uploading file"); }
    finally { setLoading(false); }
  };

  const createProject = async () => {
    const name = prompt("Enter new project name:");
    if (!name) return;
    try {
      await axios.post(`http://127.0.0.1:8000/api/projects/${name}/reset`);
      await fetchProjects();
      setSelectedProject(name);
    } catch (err) { alert("Error creating project"); }
  };

  const deleteCurrentProject = async () => {
    if (!window.confirm(`Delete project ${selectedProject} permanently?`)) return;
    try {
      await axios.delete(`http://127.0.0.1:8000/api/projects/${selectedProject}`);
      await fetchProjects();
      setSelectedProject(projects[0] || "");
    } catch (err) { alert("Error deleting project"); }
  };

  const resetCurrentProject = async () => {
    if (!window.confirm(`Clear all documents in ${selectedProject}?`)) return;
    try {
      await axios.post(`http://127.0.0.1:8000/api/projects/${selectedProject}/reset`);
      fetchSources();
    } catch (err) { alert("Error resetting project"); }
  };

  const renameCurrentProject = async () => {
    const newName = prompt("Enter new name for project:", selectedProject);
    if (!newName || newName === selectedProject) return;
    try {
      await axios.post(`http://127.0.0.1:8000/api/projects/${selectedProject}/rename?new_name=${newName}`);
      await fetchProjects();
      setSelectedProject(newName);
    } catch (err) { alert("Error renaming project"); }
  };

  const askQuestion = async () => {
    if (!question) return;
    const currentQ = question;
    setQuestion("");
    setLoading(true);
    
    // מוסיפים זמנית לקליינט כדי שהמשתמש יראה מיד, מונגו יטפל בשמירה האמיתית בשרת
    setChatHistory(prev => [...prev, { role: 'user', text: currentQ }, { role: 'ai', text: "" }]);

    try {
      const response = await fetch(`http://127.0.0.1:8000/ask?question=${encodeURIComponent(currentQ)}&project=${selectedProject}&session_id=user_1&system_prompt=${encodeURIComponent(systemPrompt)}&user_model=${selectedModel}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let acc = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        setChatHistory(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'ai', text: acc };
          return updated;
        });
      }
    } catch (err) { alert("Error getting response"); }
    finally { setLoading(false); }
  };

  const clearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear the entire chat history for this project?")) return;
    try {
      await axios.post(`http://127.0.0.1:8000/clear_memory?project=${selectedProject}&session_id=user_1`);
      setChatHistory([]);
    } catch (err) { alert("Error clearing history"); }
  };

  const saveAsSource = async (text) => {
    setLoading(true);
    try {
      const res = await axios.post(`http://127.0.0.1:8000/api/ingest/text/smart?project=${selectedProject}`, { content: text });
      alert(`Saved as: ${res.data.suggested_title}`);
      fetchSources();
    } catch (err) { alert("Error saving source"); }
    finally { setLoading(false); }
  };

  const deleteSource = async (name) => {
    if (!window.confirm(`Delete ${name}?`)) return;
    try {
      await axios.delete(`http://127.0.0.1:8000/api/projects/${selectedProject}/sources?source_name=${name}`);
      fetchSources();
    } catch (err) { alert("Error deleting source"); }
  };

  const renameSource = async (oldName) => {
    const newName = prompt("Rename source to:", oldName);
    if (!newName || newName === oldName) return;
    try {
      await axios.post(`http://127.0.0.1:8000/api/projects/${selectedProject}/sources/rename?old_name=${encodeURIComponent(oldName)}&new_name=${encodeURIComponent(newName)}`);
      fetchSources();
    } catch (err) { alert("Error renaming source"); }
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900" dir="rtl">
      
      {/* --- Sidebar --- */}
      <div className="w-72 bg-slate-950 text-slate-200 p-5 flex flex-col gap-6 shadow-2xl overflow-y-auto custom-scrollbar">
        <h2 className="text-2xl font-black tracking-tighter text-blue-500 border-b border-slate-800 pb-2">RAG OS</h2>
        
        {/* Section 1: AI Configuration */}
        <section className="space-y-3">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500">LLM Configuration</h3>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Model Provider</label>
            <select 
              className="w-full bg-slate-900 border border-slate-800 rounded-md p-2 text-xs outline-none focus:border-blue-600 transition"
              value={selectedModel} 
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {availableModels.map(m => (
                <option 
                  key={m.id} 
                  value={m.id}
                  disabled={!m.configured}
                >
                  {m.name} {m.configured ? '' : '(Not configured)'}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">System Instructions</label>
            <textarea 
              className="w-full bg-slate-900 border border-slate-800 rounded-md p-2 text-[11px] h-24 outline-none focus:border-blue-600 transition resize-none"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
            />
          </div>
        </section>

        {/* Section 2: Project Management */}
        <section className="space-y-3 pt-4 border-t border-slate-800">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Project Workspace</h3>
          <div className="flex gap-2">
            <select 
              className="flex-1 bg-slate-900 border border-slate-800 rounded-md p-2 text-xs outline-none focus:border-blue-600 transition"
              value={selectedProject} 
              onChange={(e) => setSelectedProject(e.target.value)}
            >
              {projects.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={createProject} className="bg-blue-600 hover:bg-blue-500 px-3 rounded-md text-white font-bold transition" title="New Project">+</button>
          </div>
          
          <div className="grid grid-cols-3 gap-1">
            <button onClick={renameCurrentProject} className="text-[9px] bg-slate-900 border border-slate-800 hover:bg-slate-800 py-1 rounded">Rename</button>
            <button onClick={resetCurrentProject} className="text-[9px] bg-slate-900 border border-slate-800 hover:bg-amber-900/30 py-1 rounded">Reset</button>
            <button onClick={deleteCurrentProject} className="text-[9px] bg-slate-900 border border-slate-800 hover:bg-red-900/30 py-1 rounded text-red-400">Delete</button>
          </div>
        </section>

        {/* Section 3: Data Sources */}
        <section className="space-y-3 pt-4 border-t border-slate-800 flex-1">
          <div className="flex justify-between items-center">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Knowledge Base</h3>
            <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded-full">{sources.length}</span>
          </div>
          
          <div className="relative group">
             <input type="file" onChange={uploadFile} id="file-upload" className="hidden" />
             <label htmlFor="file-upload" className="flex items-center justify-center w-full py-2 border-2 border-dashed border-slate-800 rounded-md text-[10px] text-slate-400 hover:border-blue-600 hover:text-blue-500 cursor-pointer transition">
                + Upload Documents (PDF/Docx)
             </label>
          </div>

          <div className="space-y-1 mt-2 max-h-48 overflow-y-auto custom-scrollbar">
            {sources.map((source) => (
              <div key={source} className="flex items-center justify-between bg-slate-900/50 p-2 rounded border border-transparent hover:border-slate-700 group transition">
                <span className="text-[10px] text-slate-400 truncate flex-1" title={source}>{source}</span>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => renameSource(source)} className="p-1 hover:text-blue-400"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg></button>
                  <button onClick={() => deleteSource(source)} className="p-1 hover:text-red-500"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <button onClick={clearHistory} className="mt-auto py-2 bg-slate-900 border border-red-900/50 text-red-500 hover:bg-red-950 rounded text-[11px] font-bold transition">
          Clear Chat History
        </button>
      </div>

      {/* --- Main Chat --- */}
      <div className="flex-1 flex flex-col relative">
        <header className="h-14 bg-white border-b flex items-center justify-between px-8 shadow-sm">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <h1 className="text-sm font-bold text-slate-700">Active Project: <span className="text-blue-600">{selectedProject}</span></h1>
          </div>
          <div className="text-[10px] text-slate-400 font-mono uppercase tracking-widest">{selectedModel}</div>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
          {chatHistory.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-start' : 'items-end'}`}>
              <div className={`max-w-[85%] p-4 rounded-xl shadow-sm ${
                msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
              }`}>
                <div className="prose prose-sm max-w-none text-inherit leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                </div>
              </div>
              <div className="flex gap-4 mt-2 px-1">
                <button onClick={() => navigator.clipboard.writeText(msg.text)} className="text-[9px] uppercase tracking-tighter text-slate-400 hover:text-blue-500 font-bold transition">Copy</button>
                {msg.role === 'ai' && (
                  <button onClick={() => saveAsSource(msg.text)} className="text-[9px] uppercase tracking-tighter text-slate-400 hover:text-green-600 font-bold transition">+ Keep as Source</button>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="flex items-center gap-2 text-blue-600 text-xs font-bold px-4"><div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce" /> Processing...</div>}
          <div ref={chatEndRef} />
        </div>

        <div className="p-6 bg-white border-t">
          <div className="max-w-4xl mx-auto flex gap-3 items-end">
            <textarea 
              className="flex-1 bg-slate-100 border-transparent rounded-lg px-5 py-3 text-sm focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none transition resize-none min-h-[84px] max-h-[200px] overflow-y-auto align-middle"
              rows={1}
              value={question} 
              onChange={(e) => {
                setQuestion(e.target.value);
                // גורם לתיבה לגדול אוטומטית למטה כשהטקסט מתארך
                e.target.style.height = 'auto';
                e.target.style.height = `${e.target.scrollHeight}px`;
              }}
              onKeyDown={(e) => {
                // לחיצה על אנטר רגיל (בלי שיפט) שולחת את השאלה
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault(); // מונע ירידת שורה מיותרת ברגע השליחה
                  askQuestion();
                  // מחזיר את התיבה לגובה המקורי של שורה אחת לאחר השליחה
                  e.target.style.height = 'auto';
                }
                // לחיצה על Shift + Enter תרד שורה כרגיל
              }}
              placeholder="Ask anything about your data..."
            />
            <button onClick={askQuestion} className="p-3 rounded-xl bg-blue-600 text-white">
              <Sparkles size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;