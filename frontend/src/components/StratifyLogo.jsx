// Style 1: Minimal Pulse (ChatGPT-like)
export function MinimalPulseLogo({ size = 'md' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  };

  return (
    <div className={`${sizes[size]} relative`}>
      {/* Outer pulse ring */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-500 to-accent-600 animate-ping opacity-20"></div>
      
      {/* Main circle */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-600 to-accent-600 animate-pulse-slow shadow-2xl">
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white font-black" style={{ 
            fontSize: size === 'xl' ? '2.5rem' : size === 'lg' ? '1.75rem' : size === 'md' ? '1.25rem' : '0.875rem',
            textShadow: '0 2px 10px rgba(0,0,0,0.3)'
          }}>
            S
          </span>
        </div>
      </div>
      
      {/* Subtle glow */}
      <div className="absolute inset-[-20%] rounded-full bg-primary-500/20 blur-xl animate-pulse-slow"></div>
    </div>
  );
}

// Style 2: Rotating Hexagon (GitHub Copilot-like)
export function HexagonLogo({ size = 'md' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  };

  return (
    <div className={`${sizes[size]} relative`}>
      {/* Rotating hexagon */}
      <div className="absolute inset-0 animate-spin-slow" style={{ animationDuration: '12s' }}>
        <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-2xl">
          <defs>
            <linearGradient id="hexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1E3A8A" />
              <stop offset="50%" stopColor="#7C3AED" />
              <stop offset="100%" stopColor="#EC4899" />
            </linearGradient>
          </defs>
          <polygon 
            points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" 
            fill="url(#hexGrad)"
            stroke="white"
            strokeWidth="2"
          />
        </svg>
      </div>
      
      {/* Center S */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-white font-black z-10" style={{ 
          fontSize: size === 'xl' ? '2rem' : size === 'lg' ? '1.5rem' : size === 'md' ? '1rem' : '0.75rem',
          textShadow: '0 2px 8px rgba(0,0,0,0.4)'
        }}>
          S
        </span>
      </div>
    </div>
  );
}

// Style 3: Gradient Orb (Perplexity-like)
export function GradientOrbLogo({ size = 'md' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  };

  return (
    <div className={`${sizes[size]} relative`}>
      {/* Floating orb with gradient */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-400 via-accent-500 to-pink-600 animate-float shadow-2xl"
           style={{ 
             boxShadow: '0 10px 40px rgba(124, 58, 237, 0.4), inset 0 -20px 40px rgba(0,0,0,0.2), inset 0 20px 40px rgba(255,255,255,0.2)'
           }}>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white font-black" style={{ 
            fontSize: size === 'xl' ? '2.5rem' : size === 'lg' ? '1.75rem' : size === 'md' ? '1.25rem' : '0.875rem',
            textShadow: '0 2px 10px rgba(0,0,0,0.5)'
          }}>
            S
          </span>
        </div>
      </div>
      
      {/* Glow layers */}
      <div className="absolute inset-[-10%] rounded-full bg-gradient-to-br from-primary-500/30 to-accent-500/30 blur-xl animate-pulse-slow"></div>
    </div>
  );
}

// Style 4: Spinning Ring (Claude-like)
export function SpinningRingLogo({ size = 'md' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  };

  return (
    <div className={`${sizes[size]} relative`}>
      {/* Spinning ring */}
      <div className="absolute inset-0 rounded-full animate-spin-slow" style={{ animationDuration: '10s' }}>
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-500 via-accent-500 to-pink-500 opacity-90"
             style={{ 
               clipPath: 'polygon(0% 0%, 100% 0%, 100% 30%, 0% 30%)',
               boxShadow: '0 0 20px rgba(124, 58, 237, 0.5)'
             }}>
        </div>
      </div>
      
      {/* Inner circle */}
      <div className="absolute inset-[15%] rounded-full bg-gradient-to-br from-primary-600 to-accent-600 shadow-xl">
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white font-black" style={{ 
            fontSize: size === 'xl' ? '2rem' : size === 'lg' ? '1.5rem' : size === 'md' ? '1rem' : '0.75rem',
            textShadow: '0 2px 8px rgba(0,0,0,0.4)'
          }}>
            S
          </span>
        </div>
      </div>
    </div>
  );
}

// Main export - you can switch between styles
export default MinimalPulseLogo; // Change this to try different styles
