import { Link, useLocation } from "react-router-dom";
import { FileText, Upload, ClipboardList } from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { to: "/", label: "Upload", icon: Upload },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="bg-blue-600 p-1.5 rounded-lg">
              <FileText size={20} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-gray-900 text-lg leading-none block">
                Magriplast
              </span>
              <span className="text-xs text-gray-500 leading-none block">
                Document Verification
              </span>
            </div>
          </Link>

          {/* Nav Links */}
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={clsx(
                  "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  location.pathname === to
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}