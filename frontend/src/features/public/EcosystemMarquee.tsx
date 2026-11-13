import { useState } from "react";
import { Pause, Play } from "lucide-react";

const participants = [
  "Buyers",
  "Suppliers",
  "Distributors",
  "Investors",
  "Partners",
];

export function EcosystemMarquee() {
  const [paused, setPaused] = useState(false);
  return (
    <div className="market-strip">
      <span>ONE CONNECTED BUSINESS ECOSYSTEM</span>
      <div
        className="ecosystem-marquee"
        role="group"
        aria-label="Business ecosystem"
        tabIndex={0}
        data-paused={paused}
      >
        <p className="ecosystem-accessible">{participants.join(", ")}</p>
        <div className="ecosystem-track" aria-hidden="true">
          {[0, 1].map((copy) => (
            <div className="ecosystem-sequence" key={copy}>
              {participants.map((name) => (
                <span key={name}>
                  {name}
                  <i>✳</i>
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
      <button
        className="icon-button ecosystem-toggle"
        type="button"
        aria-label={
          paused ? "Resume ecosystem motion" : "Pause ecosystem motion"
        }
        aria-pressed={paused}
        onClick={() => setPaused(!paused)}
      >
        {paused ? (
          <Play size={16} aria-hidden="true" />
        ) : (
          <Pause size={16} aria-hidden="true" />
        )}
      </button>
    </div>
  );
}
