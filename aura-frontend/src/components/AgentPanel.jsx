import { useState, useEffect, useRef } from "react";

export default function AgentPanel({ agents }) {
  const [visible, setVisible] = useState([]);
  const timers = useRef([]);

  useEffect(() => {
    if (!agents) return;

    timers.current.forEach(clearTimeout);
    timers.current = [];
    setVisible([]);

    agents.forEach((a, i) => {
      const t = setTimeout(() => {
        setVisible(prev => [...prev, a]);
      }, i * 700);

      timers.current.push(t);
    });

    return () => timers.current.forEach(clearTimeout);
  }, [agents]);

  return (
    <div>
      <h3>🤖 Agents</h3>

      {visible.map((a, i) => (
        <div key={i}>
          {a.agent} → {a.message}
        </div>
      ))}
    </div>
  );
}