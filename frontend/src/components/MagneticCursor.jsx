import { useEffect, useState } from 'react';

export default function MagneticCursor() {
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
  const [trails, setTrails] = useState([]);
  const [ripples, setRipples] = useState([]);

  useEffect(() => {
    let trailId = 0;
    let rippleId = 0;

    const handleMouseMove = (e) => {
      const { clientX, clientY } = e;
      setCursorPos({ x: clientX, y: clientY });

      // Add trail particle
      const newTrail = {
        id: trailId++,
        x: clientX,
        y: clientY,
      };
      
      setTrails(prev => [...prev.slice(-10), newTrail]);
    };

    // Ripple effect on click
    const handleClick = (e) => {
      const newRipple = {
        id: rippleId++,
        x: e.clientX,
        y: e.clientY,
      };
      
      setRipples(prev => [...prev, newRipple]);
      
      // Remove ripple after animation completes
      setTimeout(() => {
        setRipples(prev => prev.filter(r => r.id !== newRipple.id));
      }, 1000);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('click', handleClick);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('click', handleClick);
    };
  }, []);

  return (
    <>
      {/* Cursor Dot */}
      <div
        className="cursor-dot"
        style={{
          left: `${cursorPos.x}px`,
          top: `${cursorPos.y}px`,
          transform: 'translate(-50%, -50%)',
        }}
      />
      
      {/* Cursor Ring */}
      <div
        className="cursor-ring"
        style={{
          left: `${cursorPos.x}px`,
          top: `${cursorPos.y}px`,
          transform: 'translate(-50%, -50%)',
        }}
      />
      
      {/* Cursor Trails */}
      {trails.map((trail) => (
        <div
          key={trail.id}
          className="cursor-trail"
          style={{
            left: `${trail.x}px`,
            top: `${trail.y}px`,
            transform: 'translate(-50%, -50%)',
          }}
        />
      ))}
      
      {/* Ripple Effects */}
      {ripples.map((ripple) => (
        <div
          key={ripple.id}
          className="ripple-effect"
          style={{
            left: `${ripple.x}px`,
            top: `${ripple.y}px`,
          }}
        />
      ))}
    </>
  );
}
