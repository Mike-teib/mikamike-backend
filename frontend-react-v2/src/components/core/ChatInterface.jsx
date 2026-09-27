import React, { useState, useRef, useEffect } from 'react';
import katex from 'katex';
import { Send, Bot, User, Sparkles } from 'lucide-react';

/**
 * Helper to render math formulas via KaTeX inside markdown-style text.
 */
function renderMathContent(text) {
  if (!text) return null;
  // Replace inline LaTeX $...$ or \(...\)
  const parts = text.split(/(\$\$[\s\S]*?\$\$|\$.*?\$)/g);
  return parts.map((part, index) => {
    if (part.startsWith('$$') && part.endsWith('$$')) {
      const math = part.slice(2, -2);
      try {
        const html = katex.renderToString(math, { displayMode: true, throwOnError: false });
        return <div key={index} dangerouslySetInnerHTML={{ __html: html }} style={{ margin: '0.5rem 0' }} />;
      } catch (e) {
        return <code key={index}>{part}</code>;
      }
    } else if (part.startsWith('$') && part.endsWith('$')) {
      const math = part.slice(1, -1);
      try {
        const html = katex.renderToString(math, { displayMode: false, throwOnError: false });
        return <span key={index} dangerouslySetInnerHTML={{ __html: html }} />;
      } catch (e) {
        return <code key={index}>{part}</code>;
      }
    }
    return <span key={index}>{part}</span>;
  });
}

export default function ChatInterface({ activeSubject, activeLevel, activeExercise, inputFormula, onInputChange }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: 'Bonjour ! Je suis ton assistant Pédagogique MIKAMIKE. Je t\'accompagne en **' + activeSubject + '** (' + activeLevel + '). Pose-moi une question sur le cours ou un exercice ! Ex: *"Comment calculer le discriminant $\\Delta = b^2 - 4ac$ ?"*'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  // Sync external math keyboard input into chat box
  useEffect(() => {
    if (inputFormula) {
      setInputText(prev => prev + inputFormula);
      if (onInputChange) onInputChange('');
    }
  }, [inputFormula, onInputChange]);

  const handleSend = (e) => {
    e?.preventDefault();
    if (!inputText.trim()) return;

    const userMsg = { id: Date.now(), sender: 'user', text: inputText };
    setMessages(prev => [...prev, userMsg]);
    const currentInput = inputText;
    setInputText('');

    // Simulate pedagogical response
    setTimeout(() => {
      let botResponse = "Je comprends ta question sur *" + currentInput + "*. ";
      if (currentInput.includes('P1A1') || currentInput.includes('second degré') || currentInput.includes('delta')) {
        botResponse += "Pour résoudre $ax^2 + bx + c = 0$, on calcule d'abord le discriminant : $$\\Delta = b^2 - 4ac$$\n- Si $\\Delta > 0$, il y a deux racines : $x_1 = \\frac{-b - \\sqrt{\\Delta}}{2a}$ et $x_2 = \\frac{-b + \\sqrt{\\Delta}}{2a}$.\n- Si $\\Delta = 0$, une racine double : $x_0 = -\\frac{b}{2a}$.";
      } else if (currentInput.includes('P1A2') || currentInput.includes('dérivée')) {
        botResponse += "Pour dériver une fonction polynôme $f(x) = ax^n$, la formule exacte est : $$f'(x) = a \\cdot n \\cdot x^{n-1}$$ Par exemple, la dérivée de $f(x) = 3x^2 - 5x + 2$ est $f'(x) = 6x - 5$.";
      } else {
        botResponse += "Analysons ensemble l'étape : $$f(x) = \\int g(x) dx$$ N'hésite pas à utiliser l'ardoise graphique ou le clavier mathématique ci-contre !";
      }

      setMessages(prev => [...prev, { id: Date.now(), sender: 'bot', text: botResponse }]);
    }, 600);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '0.75rem 1rem', background: '#0f172a', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Sparkles size={18} color="#60a5fa" />
        <h3 style={{ fontSize: '0.95rem', fontWeight: '600' }}>Assistant IA MIKAMIKE — {activeSubject}</h3>
      </div>

      {/* Messages Feed */}
      <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {messages.map(msg => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '0.5rem',
              alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%'
            }}
          >
            {msg.sender === 'bot' && (
              <div style={{ width: 32, height: 32, borderRadius: '50%', overflow: 'hidden', border: '1px solid #10b981', flexShrink: 0 }}>
                <img src="https://mikamike.fr/wp-content/uploads/2026/07/cropped-cropped-03-mika-portrait-logo-1.jpg" alt="Mika avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            )}
            <div
              style={{
                background: msg.sender === 'user' ? '#0284c7' : '#1e293b',
                color: '#f8fafc',
                padding: '0.65rem 0.9rem',
                borderRadius: '12px',
                borderTopRightRadius: msg.sender === 'user' ? '2px' : '12px',
                borderTopLeftRadius: msg.sender === 'bot' ? '2px' : '12px',
                border: msg.sender === 'bot' ? '1px solid rgba(16, 185, 129, 0.3)' : 'none',
                fontSize: '0.875rem',
                lineHeight: '1.4'
              }}
            >
              {renderMathContent(msg.text)}
            </div>
            {msg.sender === 'user' && (
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <User size={16} color="#fff" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} style={{ padding: '0.75rem', background: '#0f172a', borderTop: '1px solid #334155', display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Pose une question ou saisis une formule mathématique..."
          style={{
            flex: 1,
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
            padding: '0.5rem 0.85rem',
            color: '#f8fafc',
            fontSize: '0.875rem'
          }}
          aria-label="Champ de message pour le chat pédagogique"
        />
        <button type="submit" className="btn btn-primary" aria-label="Envoyer le message">
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
