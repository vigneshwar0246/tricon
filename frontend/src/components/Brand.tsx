import { AudioLines } from "lucide-react";
import { Link } from "react-router-dom";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="brand" aria-label="AI Voice Assistant home">
      <span className="brand-icon"><AudioLines aria-hidden="true" /></span>
      {!compact && <span>AI Voice<br />Assistant</span>}
    </Link>
  );
}
