import { useState, useRef, useEffect } from 'react'
import './index.css'
import MapComponent from './MapComponent';
import AnalyticsChart from './AnalyticsChart';

function Dashboard() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [processedVideo, setProcessedVideo] = useState(null)
  const [stats, setStats] = useState({ poacher: '0%', weapon: '0%', mailSent: 'No', timestamp: '-' })
  const [history, setHistory] = useState([])

  const [mode, setMode] = useState('upload'); // 'upload' or 'camera'
  const videoRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [videoStream, setVideoStream] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [activeThreats, setActiveThreats] = useState([]);
  const [whatsappConnected, setWhatsappConnected] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [notification, setNotification] = useState(null); // For visual alerts

  // Get User Location on Mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation([position.coords.latitude, position.coords.longitude]);
        },
        (error) => {
          console.error("Error getting location:", error);
          // Fallback to default if denied
          setUserLocation([-24.0, 31.5]);
        }
      );
    } else {
      setUserLocation([-24.0, 31.5]);
    }
  }, []);

  // Audio Context Ref to persist across renders and avoid auto-play policy issues
  const audioCtxRef = useRef(null);

  // Simulate random location near center for demo
  const generateRandomLocation = () => {
    const baseLat = -24.0;
    const baseLng = 31.5;
    return [baseLat + (Math.random() - 0.5) * 0.1, baseLng + (Math.random() - 0.5) * 0.1];
  };

  // Initialize Audio Context on user interaction
  const initAudio = () => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
  };

  // Siren Logic (Web Audio API)
  const playSiren = () => {
    if (!soundEnabled) return;

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    oscillator.type = 'sawtooth';
    oscillator.frequency.setValueAtTime(440, audioCtx.currentTime);
    oscillator.frequency.linearRampToValueAtTime(880, audioCtx.currentTime + 0.5);
    oscillator.frequency.linearRampToValueAtTime(440, audioCtx.currentTime + 1.0);

    gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 1.0);

    oscillator.start();
    oscillator.stop(audioCtx.currentTime + 1.0);
  };

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFile(e.target.files[0])
    }
  }

  const addToHistory = (newStats, type) => {
    setHistory(prev => [{ ...newStats, type, id: Date.now() }, ...prev].slice(0, 10)); // Keep last 10
  };

  const handleUpload = async (selectedFile = null) => {
    const fileToUpload = selectedFile || file;
    if (!fileToUpload) return

    setUploading(true)
    setProcessedVideo(null)
    setStats({ poacher: '...', weapon: '...', mailSent: '...', timestamp: 'Processing...' })

    const formData = new FormData()
    formData.append('file', fileToUpload)

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json()
      console.log("Upload success:", data)

      // Start polling for results
      const filename = fileToUpload.name
      const pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/results/${filename}?t=${Date.now()}`)
          const resultData = await res.json()

          if (resultData.status === 'completed') {
            clearInterval(pollInterval)
            setUploading(false)
            setProcessedVideo(resultData.video_url)

            const newStats = {
              poacher: `${resultData.poacher_confidence}%`,
              weapon: `${resultData.weapon_confidence}%`,
              mailSent: resultData.mail_sent,
              timestamp: resultData.timestamp || new Date().toLocaleString()
            };

            setStats(newStats)
            addToHistory(newStats, 'File Upload');

            // Trigger Alert Sound & Map Update
            if (parseFloat(newStats.poacher) > 0 || parseFloat(newStats.weapon) > 0) {
              playSiren();
              setActiveThreats(prev => [...prev, {
                position: generateRandomLocation(),
                type: parseFloat(newStats.poacher) > 0 ? 'Poacher' : 'Weapon',
                confidence: parseFloat(newStats.poacher) > 0 ? newStats.poacher : newStats.weapon
              }]);

              if (whatsappConnected) {
                console.log("📲 Sending WhatsApp alert to Ranger Group...");
                showNotification("📲 WhatsApp Alert Sent to Rangers!", "success");
                // In a real app, this would call a backend endpoint
              }
            }

          } else if (resultData.status === 'error') {
            clearInterval(pollInterval)
            setUploading(false)
            alert(`Analysis failed: ${resultData.message}`)
          }
        } catch (err) {
          console.error("Polling error:", err)
        }
      }, 2000)

    } catch (error) {
      console.error('Error uploading file:', error)
      alert(`Upload failed: ${error.message}`)
      setUploading(false)
      setStats({ poacher: '-', weapon: '-', mailSent: '-', timestamp: 'Failed' })
    }
  }

  // Camera Logic
  const startCamera = async () => {
    setMode('camera');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      setVideoStream(stream);
      setCameraActive(true);
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Could not access camera. Please allow permissions.");
      setMode('upload');
    }
  };

  const stopCamera = () => {
    if (videoStream) {
      videoStream.getTracks().forEach(track => track.stop());
    }
    setVideoStream(null);
    setCameraActive(false);
    setMode('upload');
  };

  // Attach stream to video element
  useEffect(() => {
    if (videoRef.current && videoStream) {
      videoRef.current.srcObject = videoStream;
      videoRef.current.onloadedmetadata = () => {
        videoRef.current.play().catch(e => console.error("Play error:", e));
      };
    }
  }, [videoStream]);

  // Manual Capture Logic (HTTP)
  const captureFrame = async () => {
    if (!videoRef.current || !cameraActive || mode !== 'camera') return;

    const video = videoRef.current;
    if (video.readyState !== 4) return;

    const offscreen = document.createElement('canvas');
    const scale = 640 / video.videoWidth;
    offscreen.width = 640;
    offscreen.height = video.videoHeight * scale;
    const offCtx = offscreen.getContext('2d');
    offCtx.drawImage(video, 0, 0, offscreen.width, offscreen.height);

    offscreen.toBlob(async (blob) => {
      if (!blob) return;
      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');

      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/detect_frame', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        const data = await res.json();

        if (data.image) {
          setProcessedVideo(data.image);
        }

        const newStats = {
          poacher: `${Math.round(data.summary.poacher.confidence * 100)}%`,
          weapon: `${Math.round(data.summary.weapon.confidence * 100)}%`,
          mailSent: data.summary.mail.detected ? 'Yes' : 'No',
          timestamp: data.summary.timestamp || new Date().toLocaleTimeString()
        };

        setStats(newStats);

        // Only add to history if something interesting happened
        if (parseFloat(newStats.poacher) > 0 || parseFloat(newStats.weapon) > 0) {
          addToHistory(newStats, 'Live Camera');
          playSiren();
        }

      } catch (err) {
        console.error("Detection error:", err);
      }

      // Schedule next frame
      if (cameraActive && mode === 'camera') {
        setTimeout(captureFrame, 500); // 2 FPS
      }
    }, 'image/jpeg');
  };

  // Start loop when camera is ready
  useEffect(() => {
    if (cameraActive && mode === 'camera') {
      const checkVideo = setInterval(() => {
        if (videoRef.current && videoRef.current.readyState === 4) {
          clearInterval(checkVideo);
          console.log("Camera ready, starting detection loop...");
          captureFrame();
        }
      }, 500);
      return () => clearInterval(checkVideo);
    }
  }, [cameraActive, mode]);


  return (
    <div className="app-container">
      {/* Notification Toast */}
      {notification && (
        <div style={{
          position: 'fixed',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: notification.type === 'success' ? '#00C851' : '#33b5e5',
          color: 'white',
          padding: '10px 20px',
          borderRadius: '8px',
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          fontWeight: 'bold',
          animation: 'slideDown 0.3s ease-out'
        }}>
          {notification.message}
        </div>
      )}

      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 2rem', background: 'rgba(0,0,0,0.8)', color: 'white' }}>
        <h1 style={{ margin: 0, fontSize: '1.8rem', letterSpacing: '2px' }}>ECOEYE AI</h1>
        <nav style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button
            onClick={() => {
              setSoundEnabled(!soundEnabled);
              initAudio(); // Initialize audio on click
            }}
            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: soundEnabled ? '#00C851' : '#ff4444', padding: '5px 10px', borderRadius: '20px', cursor: 'pointer', fontSize: '0.9rem' }}
          >
            {soundEnabled ? '🔊 Sound ON' : '🔇 Sound OFF'}
          </button>

          <button
            onClick={() => {
              initAudio(); // Initialize audio on click
              if (!whatsappConnected) {
                const phone = prompt("Enter Ranger Phone Number for WhatsApp Alerts:");
                if (phone) {
                  setWhatsappConnected(true);
                  showNotification("✅ WhatsApp Connected!", "success");
                }
              } else {
                setWhatsappConnected(false);
                showNotification("❌ WhatsApp Disconnected", "info");
              }
            }}
            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: whatsappConnected ? '#25D366' : '#aaa', padding: '5px 10px', borderRadius: '20px', cursor: 'pointer', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '5px' }}
          >
            {whatsappConnected ? '✅ WhatsApp Active' : '💬 Connect WhatsApp'}
          </button>

          <a href="/profile" className="nav-link">
            My Profile 👤
          </a>
        </nav>
      </header>

      <main style={{ display: 'flex', gap: '20px', padding: '20px', minHeight: 'calc(100vh - 80px)' }}>

        {/* LEFT PANEL: Controls & History */}
        <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '350px' }}>

          {/* Control Card */}
          <div className="card control-card">
            <h3>Detection Source</h3>

            {/* Interactive Mode Selection */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '20px' }}>

              {/* Upload Card - Acts as Trigger */}
              <div style={{ position: 'relative' }}>
                <input
                  type="file"
                  id="file-upload"
                  hidden
                  onChange={(e) => {
                    handleFileChange(e);
                    if (e.target.files && e.target.files[0]) {
                      setMode('upload');
                      stopCamera();
                      const selectedFile = e.target.files[0];
                      setFile(selectedFile);
                      handleUpload(selectedFile);
                    }
                  }}
                />
                <label
                  htmlFor="file-upload"
                  className={`mode-card ${mode === 'upload' ? 'active' : ''}`}
                  style={{ height: '100%', margin: 0 }}
                >
                  <div style={{ fontSize: '2rem', marginBottom: '5px' }}>
                    {uploading ? '⏳' : '📁'}
                  </div>
                  <div>{uploading ? 'Processing...' : 'Upload File'}</div>
                </label>
              </div>

              <button
                className={`mode-card ${mode === 'camera' ? 'active' : ''}`}
                onClick={startCamera}
              >
                <div style={{ fontSize: '2rem', marginBottom: '5px' }}>📷</div>
                <div>Live Cam</div>
              </button>
            </div>

            {mode === 'camera' && (
              <div style={{ textAlign: 'center', padding: '20px', background: 'rgba(0, 200, 81, 0.1)', borderRadius: '10px', border: '1px solid #00C851' }}>
                <div style={{ color: '#00C851', fontWeight: 'bold', marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                  <div className="pulsing-dot"></div> Live Monitoring Active
                </div>
                <button className="danger-btn" onClick={stopCamera} style={{ width: 'auto', padding: '8px 20px' }}>Stop Camera</button>
              </div>
            )}
          </div>

          {/* History Card */}
          <div className="card history-card" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #333', paddingBottom: '10px', marginBottom: '10px' }}>
              <h3 style={{ margin: 0, border: 'none', padding: 0 }}>Recent Alerts 🕒</h3>
              {history.length > 0 && (
                <button
                  onClick={() => setHistory([])}
                  style={{ background: 'transparent', border: 'none', color: '#888', cursor: 'pointer', fontSize: '0.8rem', textDecoration: 'underline' }}
                >
                  Clear All
                </button>
              )}
            </div>

            <div className="history-list">
              {history.length === 0 ? (
                <p style={{ color: '#888', fontStyle: 'italic', textAlign: 'center', marginTop: '20px' }}>No detections yet...</p>
              ) : (
                history.map((item) => (
                  <div key={item.id} className="history-item">
                    <div className="history-time">{item.timestamp}</div>
                    <div className="history-details">
                      {parseFloat(item.poacher) > 0 && <span className="tag poacher">Poacher {item.poacher}</span>}
                      {parseFloat(item.weapon) > 0 && <span className="tag weapon">Weapon {item.weapon}</span>}
                      {parseFloat(item.poacher) === 0 && parseFloat(item.weapon) === 0 && <span className="tag" style={{ background: '#444' }}>Safe</span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Analytics Card */}
          <div className="card analytics-card" style={{ marginTop: '20px' }}>
            <h3>📊 Detection Trends</h3>
            <AnalyticsChart history={history} />
          </div>
        </div>

        {/* RIGHT PANEL: Visuals & Stats */}
        <div style={{ flex: '3', display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Video Feed */}
          <div className="video-wrapper">
            {mode === 'camera' && (
              <video ref={videoRef} autoPlay playsInline muted className="bg-video" />
            )}

            {processedVideo ? (
              processedVideo.endsWith('.mp4') ? (
                <video src={processedVideo} controls autoPlay loop className="main-video" />
              ) : (
                <img src={processedVideo} alt="Processed" className="main-video" />
              )
            ) : (
              <div className="placeholder">
                <div className="scanner-line"></div>
                <p>Waiting for input...</p>
              </div>
            )}

            {/* Overlay Stats */}
            <div className="stats-overlay">
              <div className="stat-box">
                <span className="label">POACHER</span>
                <span className={`value ${parseFloat(stats.poacher) > 0 ? 'alert' : ''}`}>{stats.poacher}</span>
              </div>
              <div className="stat-box">
                <span className="label">WEAPON</span>
                <span className={`value ${parseFloat(stats.weapon) > 0 ? 'alert' : ''}`}>{stats.weapon}</span>
              </div>
              <div className="stat-box">
                <span className="label">EMAIL ALERT</span>
                <span className={`value ${stats.mailSent === 'Yes' ? 'success' : ''}`}>{stats.mailSent}</span>
              </div>
              <div className="stat-box time-box">
                <span className="label">LAST UPDATE</span>
                <span className="value">{stats.timestamp}</span>
              </div>
            </div>
          </div>

          {/* Map Section */}
          <div className="card map-card">
            <h3>📍 Live Threat Map</h3>
            <MapComponent activeThreats={activeThreats} userLocation={userLocation} />
          </div>

        </div>

      </main>
    </div>
  )
}

export default Dashboard
