import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
const A = "/assets/";
export function Picture({
  file,
  alt,
  priority = false,
  className = "",
}: {
  file: string;
  alt: string;
  priority?: boolean;
  className?: string;
}) {
  return (
    <picture className={className}>
      <source
        type="image/webp"
        srcSet={`${A}${file.replace(".png", "-800.webp")} 800w, ${A}${file.replace(".png", "-1280.webp")} 1280w`}
        sizes="(max-width: 700px) 100vw, 65vw"
      />
      <img
        src={A + file}
        alt={alt}
        width="1672"
        height="941"
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
      />
    </picture>
  );
}
export function Cta({
  to = "/signup",
  children = "Get started",
}: {
  to?: string;
  children?: React.ReactNode;
}) {
  return (
    <Link className="button" to={to}>
      {children}
      <ArrowUpRight size={18} />
    </Link>
  );
}
export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="eyebrow">
      <span />
      {children}
    </p>
  );
}
