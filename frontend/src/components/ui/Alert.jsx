import clsx from "clsx";

const VARIANTS = {
  error: "bg-red-50 border-red-300 text-red-800",
  warning: "bg-yellow-50 border-yellow-300 text-yellow-800",
  success: "bg-green-50 border-green-300 text-green-800",
  info: "bg-blue-50 border-blue-300 text-blue-800",
};

export default function Alert({ variant = "info", title, children, className = "" }) {
  return (
    <div className={clsx("border rounded-lg px-4 py-3", VARIANTS[variant], className)}>
      {title && <p className="font-semibold mb-1">{title}</p>}
      <div className="text-sm">{children}</div>
    </div>
  );
}