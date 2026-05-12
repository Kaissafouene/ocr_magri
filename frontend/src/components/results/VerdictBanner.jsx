import { GLOBAL_VERDICT_STYLES } from "../../utils/verdictColors";

export default function VerdictBanner({ verdict, matchResult, status, errorMessage }) {
  let bannerKey = verdict || "PENDING";
  if (status === "FAILED") {
    bannerKey = "FAILED";
  } else if (status === "REVIEW_REQUIRED") {
    bannerKey = "REVIEW_REQUIRED";
  }
  const style = GLOBAL_VERDICT_STYLES[bannerKey] || GLOBAL_VERDICT_STYLES.PENDING;

  return (
    <div className={`${style.bg} rounded-xl p-6 text-white`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl font-bold leading-none">{style.icon}</span>
          <div>
            <h2 className="text-xl font-bold">{style.label}</h2>
            <p className="text-sm opacity-90 mt-0.5">{style.description}</p>
          </div>
        </div>

        {matchResult && (
          <div className="flex items-center gap-4 text-sm shrink-0">
            <Stat label="Match" value={matchResult.match_count} color="bg-green-200 text-green-900" />
            <Stat label="Mismatch" value={matchResult.mismatch_count} color="bg-red-200 text-red-900" />
            <Stat label="Missing" value={matchResult.missing_count} color="bg-orange-200 text-orange-900" />
            <Stat label="Extra" value={matchResult.extra_count} color="bg-purple-200 text-purple-900" />
          </div>
        )}
      </div>

      {status === "FAILED" && errorMessage && (
        <p className="text-sm mt-3 opacity-90">{errorMessage}</p>
      )}

      {matchResult?.used_fuzzy_link && (
        <p className="text-xs mt-3 opacity-75">
          Fuzzy document link was used; manual verification of document references is recommended.
        </p>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className={`px-3 py-1.5 rounded-lg ${color} flex flex-col items-center min-w-[56px]`}>
      <span className="text-lg font-bold leading-none">{value}</span>
      <span className="text-xs font-medium opacity-75 mt-0.5">{label}</span>
    </div>
  );
}
