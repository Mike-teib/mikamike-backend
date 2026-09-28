import React, { useEffect, useRef, useState } from 'react';
import katex from 'katex';
import { Send, User, Sparkles, Mic, MicOff, ChevronUp, ChevronDown, BookOpen } from 'lucide-react';
import { MOCK_EXERCISES } from './ExerciseViewer';

function renderMathContent(text) {
  if (!text) return null;
  const parts = text.split(/(\$\$[\s\S]*?\$\$|\$.*?\$)/g);
  return parts.map((part, index) => {
    if (part.startsWith('$$') && part.endsWith('$$')) {
      const math = part.slice(2, -2);
      try {
        const html = katex.renderToString(math, { displayMode: true, throwOnError: false });
        return <div key={index} dangerouslySetInnerHTML={{ __html: html }} style={{ margin: '0.5rem 0' }} />;
      } catch {
        return <code key={index}>{part}</code>;
      }
    }
    if (part.startsWith('$') && part.endsWith('$')) {
      const math = part.slice(1, -1);
      try {
        const html = katex.renderToString(math, { displayMode: false, throwOnError: false });
        return <span key={index} dangerouslySetInnerHTML={{ __html: html }} />;
      } catch {
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
      text: 'Bonjour ! Je suis ton assistant Pédagogique MIKAMIKE. Je t\'accompagne en **' + activeSubject + '** (' + activeLevel + '). Pose-moi une question sur le cours ou un exercice !'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [exerciseExpanded, setExerciseExpanded] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('');
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const currentExercise = MOCK_EXERCISES[activeExercise] || null;
  const SpeechRecognition =
    typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null;
  const speechSupported = Boolean(SpeechRecognition);

  useEffect(() => {
    if (inputFormula) {
      setInputText(prev => prev + inputFormula);
      if (onInputChange) onInputChange('');
    }
  }, [inputFormula, onInputChange]);

  useEffect(() => () => {
    try {
      recognitionRef.current?.stop();
    } catch {
      // no-op
    }
  }, []);

  const handleVoiceToggle = () => {
    if (!speechSupported) {
      setVoiceStatus('La dictée vocale n’est pas prise en charge par ce navigateur.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = true;
    recognition.continuous = false;

    recognition.onstart = () => {
      setIsListening(true);
      setVoiceStatus('Écoute en cours… parle normalement.');
    };

    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i][0]?.transcript || '';
      }
      if (transcript) {
        setInputText(prev => {
          const spacer = prev && !prev.endsWith(' ') ? ' ' : '';
          return prev + spacer + transcript;
        });
      }
    };

    recognition.onerror = (event) => {
      const messagesByError = {
        'not-allowed': 'Accès au micro refusé. Autorise le micro dans le navigateur puis réessaie.',
        'service-not-allowed': 'Accès au service vocal refusé par le navigateur.',
        'audio-capture': 'Aucun micro utilisable n’a été détecté sur cet ordinateur.',
        'no-speech': 'Je n’ai rien entendu. Réessaie en parlant un peu plus près du micro.',
        'network': 'Le service de reconnaissance vocale est momentanément indisponible.'
      };
      setVoiceStatus(messagesByError[event.error] || 'La dictée vocale a rencontré un problème.');
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      setVoiceStatus('Impossible de démarrer la dictée vocale pour le moment.');
      setIsListening(false);
    }
  };

  const handleSend = (e) => {
    e?.preventDefault();
    if (!inputText.trim()) return;

    const userMsg = { id: Date.now(), sender: 'user', text: inputText };
    setMessages(prev => [...prev, userMsg]);
    const currentInput = inputText;
    setInputText('');

    setTimeout(() => {
      let botResponse = "Je comprends ta question sur *" + currentInput + "*. ";
      if (currentInput.includes('P1A1') || currentInput.includes('second degré') || currentInput.includes('delta')) {
        botResponse += "Pour résoudre $ax^2 + bx + c = 0$, on calcule d'abord le discriminant : $$\\Delta = b^2 - 4ac$$";
      } else if (currentInput.includes('P1A2') || currentInput.includes('dérivée')) {
        botResponse += "Pour dériver une fonction polynôme $f(x) = ax^n$, on utilise : $$f'(x) = a \\cdot n \\cdot x^{n-1}$$";
      } else {
        botResponse += "On avance étape par étape. Garde l’énoncé visible au-dessus pendant que tu réponds.";
      }
      setMessages(prev => [...prev, { id: Date.now(), sender: 'bot', text: botResponse }]);
    }, 600);
  };

  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className="glass-card mika-chat-shell">
      <div className="mika-chat-header">
        <Sparkles size={18} color="#60a5fa" />
        <h3>Assistant IA MIKAMIKE — {activeSubject}</h3>
      </div>

      {currentExercise && (
        <section className="mika-exercise-context" aria-label="Énoncé de l’exercice en cours">
          <div className="mika-exercise-context-head">
            <div>
              <span className="mika-exercise-kicker"><BookOpen size={14} /> Énoncé en cours</span>
              <strong>{currentExercise.id} — {currentExercise.title}</strong>
            </div>
            <button
              type="button"
              className="btn btn-outline mika-context-toggle"
              onClick={() => setExerciseExpanded(v => !v)}
              aria-expanded={exerciseExpanded}
              aria-label={exerciseExpanded ? 'Réduire l’énoncé' : 'Afficher l’énoncé'}
            >
              {exerciseExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              {exerciseExpanded ? 'Réduire' : 'Voir'}
            </button>
          </div>

          {exerciseExpanded && (
            <div className="mika-exercise-context-body">
              <p>{renderMathContent(currentExercise.statement)}</p>
              <p className="mika-exercise-question"><strong>Question :</strong> {renderMathContent(currentExercise.question)}</p>
            </div>
          )}
        </section>
      )}

      <div className="mika-messages-feed">
        {messages.map(msg => (
          <div key={msg.id} className={`mika-message-row ${msg.sender === 'user' ? 'is-user' : 'is-bot'}`}>
            {msg.sender === 'bot' && (
              <div className="mika-avatar">
                <img
                  src="https://mikamike.fr/wp-content/uploads/2026/07/cropped-cropped-03-mika-portrait-logo-1.jpg"
                  alt="Mika avatar"
                />
              </div>
            )}
            <div className="mika-message-bubble">
              {renderMathContent(msg.text)}
            </div>
            {msg.sender === 'user' && (
              <div className="mika-user-avatar"><User size={16} color="#fff" /></div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="mika-input-form">
        <button
          type="button"
          onClick={handleVoiceToggle}
          className={`btn ${isListening ? 'btn-primary' : 'btn-outline'} mika-mic-button`}
          aria-label={isListening ? 'Arrêter la dictée vocale' : 'Activer la dictée vocale'}
          title={speechSupported ? 'Dicter la réponse au micro' : 'Dictée vocale non prise en charge'}
        >
          {isListening ? <MicOff size={18} /> : <Mic size={18} />}
        </button>

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Écris ou dicte ta question…"
          aria-label="Champ de message pour le chat pédagogique"
        />

        <button type="submit" className="btn btn-primary" aria-label="Envoyer le message">
          <Send size={16} /> Envoyer
        </button>
      </form>

      <div className="mika-voice-status" aria-live="polite">
        {voiceStatus || (speechSupported ? 'Micro disponible sur ce navigateur.' : 'Dictée vocale non disponible sur ce navigateur.')}
      </div>
    </div>
  );
}
