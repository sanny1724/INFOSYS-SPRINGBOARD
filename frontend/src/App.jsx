import { useState, useRef, useEffect } from 'react'
import './index.css'

function App() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [processedVideo, setProcessedVideo] = useState(null)
  const [stats, setStats] = useState({ poacher: '0%', weapon: '0%', mailSent: 'No' })

  const [mode, setMode] = useState('upload'); // 'upload' or 'camera'
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [weaponPreview, setWeaponPreview] = useState(null);

  const [cameraLoading, setCameraLoading] = useState(false);
  const [videoStream, setVideoStream] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setProcessedVideo(null)
    setStats({ poacher: '...', weapon: '...', mailSent: '...' })

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      console.log("Upload success:", data)

      // Start polling for results
      const filename = file.name
      const pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/results/${filename}?t=${Date.now()}`)
          const resultData = await res.json()

          if (resultData.status === 'completed') {
            clearInterval(pollInterval)
            setUploading(false)
            setProcessedVideo(resultData.video_url)
            setStats({
              poacher: `${resultData.poacher_confidence}%`,
              weapon: `${resultData.weapon_confidence}%`,
              mailSent: resultData.mail_sent
            })
          }
        } catch (err) {
          console.error("Polling error:", err)
        }
      }, 2000)

    } catch (error) {
      console.error('Error uploading file:', error)
      setUploading(false)
    }
  }

  // Camera Logic
  const startCamera = async () => {
    setMode('camera');
    setCameraLoading(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      setVideoStream(stream);
      setCameraActive(true);
      setCameraLoading(false);
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Could not access camera. Please allow permissions.");
      setMode('upload');
      setCameraLoading(false);
    }
  };

  const stopCamera = () => {
    if (videoStream) {
      videoStream.getTracks().forEach(track => track.stop());
    }
    setVideoStream(null);
    setCameraActive(false);
    setCameraLoading(false);
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
    offscreen.width = video.videoWidth;
    offscreen.height = video.videoHeight;
    const offCtx = offscreen.getContext('2d');
    offCtx.drawImage(video, 0, 0);

    offscreen.toBlob(async (blob) => {
      if (!blob) return;
      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');

      try {
        const res = await fetch('/detect_frame', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        const data = await res.json();

        if (data.image) {
          setProcessedVideo(data.image);
        }

        setStats({
          poacher: `${Math.round(data.summary.poacher.confidence * 100)}%`,
          weapon: `${Math.round(data.summary.weapon.confidence * 100)}%`,
          mailSent: data.summary.mail.detected ? 'Yes' : 'No'
        });

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
      <header>
        <h1>ECOEYE AI</h1>
      </header>

      <main>
        <div className="dashboard">
          <div className="upload-section">
            {mode === 'upload' ? (
              <>
                <div className="upload-icon">☁️</div>
                <h3>Drop file or browse</h3>
                <input
                  type="file"
                  accept="video/*,image/*"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                  id="file-upload"
                />
                <label htmlFor="file-upload">
                  <span className="primary-btn" style={{ display: 'inline-block', marginTop: '1rem' }}>
                    Select File
                  </span>
                </label>
                {file && <p style={{ marginTop: '1rem' }}>Selected: {file.name}</p>}

                <button
                  className="primary-btn"
                  onClick={handleUpload}
                  disabled={!file || uploading}
                  style={{ width: '100%' }}
                >
                  {uploading ? 'Processing...' : 'Analyze'}
                </button>

                <div style={{ marginTop: '2rem', borderTop: '1px solid #ccc', paddingTop: '1rem', width: '100%', textAlign: 'center' }}>
                  <p>Or use Live Camera</p>
                  <button className="primary-btn" onClick={startCamera} style={{ background: 'linear-gradient(45deg, #0288D1, #29B6F6)' }}>
                    Start Camera
                  </button>
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
                <h3>Live Camera Active</h3>
                <p>Analyzing frames...</p>
                {weaponPreview && (
                  <div style={{ marginTop: '1rem', border: '2px solid red', padding: '5px' }}>
                    <p style={{ color: 'red', fontWeight: 'bold', margin: 0 }}>WEAPON DETECTED</p>
                    <img src={weaponPreview} alt="Weapon" style={{ maxWidth: '150px' }} />
                  </div>
                )}
                <button className="primary-btn" onClick={stopCamera} style={{ marginTop: 'auto', background: '#555' }}>
                  Stop Camera
                </button>
              </div>
            )}
          </div>

          <div className="preview-section">
            <div className="video-container" style={{ position: 'relative', display: 'inline-block', minWidth: '400px', minHeight: '300px', border: '2px solid #333' }}>
              {mode === 'camera' ? (
                <>
                  {/* Raw Video (Always visible as background) */}
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      display: 'block'
                    }}
                  />

                  {/* Processed Image Overlay */}
                  {processedVideo && (
                    <img
                      src={processedVideo}
                      alt="Processed Stream"
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        zIndex: 10
                      }}
                    />
                  )}

                  {!processedVideo && (
                    <div style={{ position: 'absolute', top: 10, left: 10, color: 'white', background: 'rgba(0,0,0,0.5)', padding: '5px' }}>
                      Initializing AI...
                    </div>
                  )}

                  {/* High Visibility Stats Overlay */}
                  <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    width: '100%',
                    background: 'rgba(0, 0, 0, 0.7)',
                    color: '#fff',
                    padding: '10px',
                    display: 'flex',
                    justifyContent: 'space-around',
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    zIndex: 20
                  }}>
                    <span style={{ color: parseFloat(stats.poacher) > 0 ? '#ff4444' : '#fff' }}>
                      POACHER: {stats.poacher}
                    </span>
                    <span style={{ color: parseFloat(stats.weapon) > 0 ? '#ff4444' : '#fff' }}>
                      WEAPON: {stats.weapon}
                    </span>
                    <span style={{ color: stats.mailSent === 'Yes' ? '#00C851' : '#fff' }}>
                      EMAIL SENT: {stats.mailSent}
                    </span>
                  </div>
                </>
              ) : (
                processedVideo ? (
                  processedVideo.endsWith('.mp4') ? (
                    <video src={processedVideo} controls style={{ width: '100%', height: '100%' }} />
                  ) : (
                    <img src={processedVideo} alt="Processed" style={{ maxWidth: '100%', maxHeight: '100%' }} />
                  )
                ) : (
                  <p>No video/image processed yet</p>
                )
              )}
            </div>

            <div className="stats-panel">
              <div className="stat-item">
                <span className="stat-label">Poacher Detected</span>
                <span className={`stat-value ${parseFloat(stats.poacher) > 0 ? 'danger' : ''}`}>
                  {stats.poacher}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Weapon Detected</span>
                <span className={`stat-value ${parseFloat(stats.weapon) > 0 ? 'danger' : ''}`}>
                  {stats.weapon}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Mail Status</span>
                <span className="stat-value" style={{ fontSize: '1rem' }}>
                  {stats.mailSent}
                </span>
              </div>
            </div>

            {processedVideo && (
              <button
                className="primary-btn"
                onClick={() => {
                  setFile(null);
                  setProcessedVideo(null);
                  setStats({ poacher: '0%', weapon: '0%', mailSent: 'No' });
                }}
                style={{ alignSelf: 'center', background: '#555' }}
              >
                Reset / New Upload
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
