import React, { useEffect, useState, useRef, use } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function App() {
  const [projects, setProjects] = useState([]);
  const [availableModels, setAvailableModels] = useState([]); // שמירת רשימת המודלים הזמינים 
  const [selectedModel, setSelectedModel] = useState(""); // המודל הנבחר ע"י המשתמש 
  const [selectedProject, setSelectedProject] = useState("");
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful technical assistant.");
  const chatEndRef = useRef(null);

  const uploadFile = async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  setLoading(true);
  try {
    const res = await axios.post(
      `http://127.0.0.1:8000/api/files/upload?project=${selectedProject}`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    fetchSources(); // רענון רשימת המקורות   
    alert(`הצלחה: ${res.data.message}`);
  } catch (err) {
    console.error(err);
    alert("שגיאה בהעלאת הקובץ");
  } finally {
    setLoading(false);
  }
};

const fetchModels = async () => {
  try {
    // שימוש ב-Backticks וכתובת נכונה
    const res = await axios.get(`http://127.0.0.1:8000/api/models`);
    
    // בשרת החזרנו ליסט ישיר, לכן res.data הוא המערך
    setAvailableModels(res.data);
    
    // הגדרת מודל ברירת מחדל אם נבחר מודל ראשון
    if (res.data.length > 0 && !selectedModel) {
      setSelectedModel(res.data[0]);
    }
  } catch (err) {
    console.error("Error fetching models", err);
  }
};

  // יצירת פרויקט חדש
const createProject = async () => {
  const name = prompt("הכנס שם לפרויקט החדש:");
  if (!name) return;
  
  try {
    // ב-ChromaDB, פרויקט נוצר ברגע שמעלים אליו טקסט או מאתחלים אותו
    await axios.post(`http://127.0.0.1:8000/api/projects/${name}/reset`);
    await fetchProjects(); // רענון הרשימה
    setSelectedProject(name);
    alert(`פרויקט '${name}' נוצר בהצלחה`);
  } catch (err) { alert("שגיאה ביצירת פרויקט"); }
};

// מחיקת פרויקט קיים
const deleteCurrentProject = async () => {
  if (!window.confirm(`האם אתה בטוח שברצונך למחוק את הפרויקט ${selectedProject}?`)) return;
  
  try {
    await axios.delete(`http://127.0.0.1:8000/api/projects/${selectedProject}`);
    await fetchProjects();
    alert("הפרויקט נמחק");
  } catch (err) { alert("שגיאה במחיקת פרויקט"); }
};

// ניקוי תוכן הפרויקט (מחיקת קבצים בלבד)
const resetCurrentProject = async () => {
  if (!window.confirm(`זה ימחק את כל הקבצים שסרקת לפרויקט ${selectedProject}. להמשיך?`)) return;
  
  try {
    await axios.post(`http://127.0.0.1:8000/api/projects/${selectedProject}/reset`);
    fetchSources(); // רענון רשימת המקורות  
    alert("תוכן הפרויקט נוקה");
  } catch (err) { alert("שגיאה בניקוי התוכן"); }
};

  // גלילה אוטומטית לתחתית
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
  fetchProjects();
  fetchModels(); // טעינת המודלים פעם אחת כשהאפליקציה עולה
}, []);

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const fetchProjects = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/projects');
      setProjects(res.data.projects);
      if (res.data.projects.length > 0) setSelectedProject(res.data.projects[0]);
    } catch (err) { console.error("Error fetching projects", err); }
  };

const askQuestion = async () => {
  if (!question) return;
  const currentQ = question;
  setQuestion("");
  setLoading(true);

  // הוספת השאלה של המשתמש להיסטוריה מיד
  setChatHistory(prev => [...prev, { role: 'user', text: currentQ }]);
  
  // יצירת הודעה ריקה עבור ה-AI שתתמלא בהדרגה
  setChatHistory(prev => [...prev, { role: 'ai', text: "" }]);

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/ask?question=${encodeURIComponent(currentQ)}&project=${selectedProject}&session_id=user_1&system_prompt=${encodeURIComponent(systemPrompt)}&user_model=${selectedModel}`
);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      // פענוח הצ'אנק שהגיע מהשרת
      const chunk = decoder.decode(value, { stream: true });
      accumulatedText += chunk;

      // עדכון ההודעה האחרונה בצ'אט (זאת של ה-AI) עם הטקסט המצטבר
      setChatHistory(prev => {
        const newHistory = [...prev];
        newHistory[newHistory.length - 1] = { role: 'ai', text: accumulatedText };
        return newHistory;
      });
    }
  } catch (err) {
    console.error("Streaming error:", err);
    alert("שגיאה בקבלת תשובה זורמת");
  } finally {
    setLoading(false);
  }
};

  const clearHistory = async () => {
    try {
      await axios.post(`http://127.0.0.1:8000/clear_memory?session_id=user_1`);
      setChatHistory([]);
    } catch (err) { alert("שגיאה בניקוי הזיכרון"); }
  };

  const [sources, setSources] = useState([]);

// פונקציה לשליפת המקורות
const fetchSources = async () => {
  if (!selectedProject) return;
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/projects/${selectedProject}/sources`);
    setSources(res.data.sources || []);
  } catch (err) { console.error("Error fetching sources", err); }
};

// רענון הרשימה כשמחליפים פרויקט
useEffect(() => {
  fetchSources();
}, [selectedProject]);

// פונקציה למחיקת מקור ספציפי
const deleteSource = async (sourceName) => {
  if (!window.confirm(`למחוק את המקור '${sourceName}'?`)) return;
  try {
    await axios.delete(`http://127.0.0.1:8000/api/projects/${selectedProject}/sources?source_name=${sourceName}`);
    fetchSources(); // רענון
  } catch (err) { alert("שגיאה במחיקת המקור"); }
};

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900" dir="rtl">
      
      {/* SideBar - ניהול פרויקטים ופרומפט */}
      <div className="w-64 bg-slate-900 text-white p-6 flex flex-col gap-6 shadow-2xl">
        <h2 className="text-xl font-bold border-b border-slate-700 pb-2">RAG Control</h2>
        
        <div className="space-y-4">
          <div>
            <div className="mb-2">
              <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-bold">מודל שפה</label>
              <select 
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                value={selectedModel} 
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>


            <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">ניהול פרויקטים</label>
            <div className="flex gap-2 mb-2">
              <select 
                className="flex-1 bg-slate-800 border border-slate-700 rounded p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                value={selectedProject} 
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                {projects.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <button onClick={createProject} className="bg-green-600 hover:bg-green-700 p-2 rounded transition" title="פרויקט חדש">+</button>
            </div>

            {/* כפתורי פעולה מהירים */}
            <div className="flex gap-1 justify-between">
              <button 
                onClick={resetCurrentProject} 
                className="text-[10px] bg-slate-800 hover:bg-amber-900 border border-slate-700 px-2 py-1 rounded transition"
              >
                ניקוי קבצים
              </button>
              <button 
                onClick={deleteCurrentProject} 
                className="text-[10px] bg-slate-800 hover:bg-red-900 border border-slate-700 px-2 py-1 rounded transition"
              >
                מחיקת פרויקט
              </button>
            </div>
          </div>

          {/* כפתור העלאת הקבצים ששמנו קודם */}
          <div className="pt-2 border-t border-slate-800">
            <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">הוספת דאטה</label>
            <input 
              type="file" 
              onChange={uploadFile} 
              className="block w-full text-[10px] text-slate-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-slate-800">
          <label className="block text-[10px] uppercase tracking-widest text-slate-500 mb-3 font-bold">מקורות בפרויקט ({sources.length})</label>
          <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
            {sources.length === 0 && <p className="text-[10px] text-slate-600 italic">אין מקורות סרוקים</p>}
            {sources.map((source) => (
              <div key={source} className="flex items-center justify-between bg-slate-800/50 p-2 rounded group">
                <span className="text-[10px] text-slate-300 truncate flex-1" title={source}>{source}</span>
                <button 
                  onClick={() => deleteSource(source)}
                  className="text-slate-500 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">System Prompt</label>
          <textarea 
            className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs h-32 outline-none focus:ring-1 focus:ring-blue-500"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
        </div>

        <button 
          onClick={clearHistory}
          className="mt-auto w-full py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-medium transition"
        >
          נקה היסטוריית צ'אט
        </button>

      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        
        {/* Header */}
        <header className="h-16 bg-white border-b flex items-center px-8 shadow-sm">
          <h1 className="text-lg font-semibold text-gray-700">צ'אט סוכן חכם - {selectedProject}</h1>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-slate-50">
          {chatHistory.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-[80%] p-4 rounded-2xl shadow-sm ${
                msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-none' 
                : 'bg-white text-gray-800 border border-gray-200 rounded-tl-none'
              }`}>
                <span className="text-[10px] opacity-70 block mb-1 font-bold">
                  {msg.role === 'user' ? 'אתה' : 'הסוכן'}
                </span>
                <div className="prose prose-sm max-w-none prose-slate">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          {loading && <div className="text-blue-600 text-sm animate-pulse">הסוכן כותב תשובה...</div>}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="p-6 bg-white border-t">
          <div className="max-w-4xl mx-auto flex gap-4">
            <input 
              className="flex-1 bg-gray-100 border-none rounded-xl px-6 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition"
              value={question} 
              onChange={(e) => setQuestion(e.target.value)} 
              onKeyPress={(e) => e.key === 'Enter' && askQuestion()}
              placeholder="כתוב שאלה..."
            />
            <button 
              onClick={askQuestion}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 rounded-xl font-bold transition shadow-md"
            >
              שלח
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;