export default function PageWrapper({ children, title, subtitle }) {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {(title || subtitle) && (
        <div className="mb-8">
          {title && (
            <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          )}
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
      )}
      {children}
    </main>
  );
}