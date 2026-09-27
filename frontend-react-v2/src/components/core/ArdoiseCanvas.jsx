import React, { useRef, useState, useEffect } from 'react';
import { Edit3, Eraser, Trash2, RotateCcw } from 'lucide-react';

export default function ArdoiseCanvas() {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [color, setColor] = useState('#38bdf8');
  const [lineWidth, setLineWidth] = useState(3);
  const [tool, setTool] = useState('pen'); // 'pen' | 'eraser'

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }, []);

  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;

    ctx.strokeStyle = tool === 'eraser' ? '#0f172a' : color;
    ctx.lineWidth = tool === 'eraser' ? lineWidth * 4 : lineWidth;
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  return (
    <div className="glass-card" style={{ padding: '0.75rem', background: '#0f172a', display: 'flex', flexDirection: 'column', gap: '0.5rem', height: '100%' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={() => setTool('pen')}
            className={`btn ${tool === 'pen' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '4px 8px', fontSize: '0.8rem' }}
            aria-label="Mode Crayon"
          >
            <Edit3 size={14} /> Crayon
          </button>
          <button
            onClick={() => setTool('eraser')}
            className={`btn ${tool === 'eraser' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '4px 8px', fontSize: '0.8rem' }}
            aria-label="Mode Gomme"
          >
            <Eraser size={14} /> Gomme
          </button>

          {/* Color palette */}
          <div style={{ display: 'flex', gap: '4px', marginLeft: '0.5rem' }}>
            {['#38bdf8', '#34d399', '#fbbf24', '#f43f5e', '#ffffff'].map(c => (
              <button
                key={c}
                onClick={() => { setColor(c); setTool('pen'); }}
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  backgroundColor: c,
                  border: color === c && tool === 'pen' ? '2px solid #fff' : 'none',
                  cursor: 'pointer'
                }}
                aria-label={`Couleur ${c}`}
              />
            ))}
          </div>
        </div>

        <button onClick={clearCanvas} className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '0.8rem', color: '#f43f5e' }} aria-label="Effacer l'ardoise">
          <Trash2 size={14} /> Effacer
        </button>
      </div>

      {/* Canvas Area */}
      <div style={{ flex: 1, minHeight: '220px', background: '#090d16', borderRadius: '8px', border: '1px dashed #334155', position: 'relative' }}>
        <canvas
          ref={canvasRef}
          width={600}
          height={320}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
          style={{ width: '100%', height: '100%', cursor: tool === 'eraser' ? 'cell' : 'crosshair' }}
          aria-label="Ardoise graphique de brouillon"
        />
      </div>
    </div>
  );
}
