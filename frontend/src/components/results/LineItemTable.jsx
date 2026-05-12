import { useState } from "react";
import LineVerdictBadge from "./LineVerdictBadge";
import ConfidenceIndicator from "./ConfidenceIndicator";
import { LINE_VERDICT_STYLES } from "../../utils/verdictColors";
import { formatQty, formatCurrency } from "../../utils/formatters";
import clsx from "clsx";
import { ChevronDown, ChevronUp } from "lucide-react";

export default function LineItemTable({ lineVerdicts }) {
  const [expandedRows, setExpandedRows] = useState(new Set());

  if (!lineVerdicts || lineVerdicts.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400 text-sm">
        No line items to display
      </div>
    );
  }

  const toggleRow = (idx) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
            <th className="text-left px-4 py-3 font-semibold">Ref / Description</th>
            {/* BC */}
            <th className="text-right px-3 py-3 font-semibold border-l border-gray-200">
              <span className="text-blue-600">BC</span> Qty
            </th>
            <th className="text-right px-3 py-3 font-semibold text-blue-600">Price</th>
            {/* BL */}
            <th className="text-right px-3 py-3 font-semibold border-l border-gray-200">
              <span className="text-teal-600">BL</span> Qty
            </th>
            {/* FACTURE */}
            <th className="text-right px-3 py-3 font-semibold border-l border-gray-200">
              <span className="text-violet-600">FAC</span> Qty
            </th>
            <th className="text-right px-3 py-3 font-semibold text-violet-600">Price</th>
            <th className="text-right px-3 py-3 font-semibold text-violet-600">TVA%</th>
            {/* Verdict */}
            <th className="text-center px-4 py-3 font-semibold border-l border-gray-200">
              Verdict
            </th>
            <th className="px-3 py-3" />
          </tr>
        </thead>
        <tbody>
          {lineVerdicts.map((line, idx) => {
            const style = LINE_VERDICT_STYLES[line.verdict] || LINE_VERDICT_STYLES.PARTIAL_DATA;
            const isExpanded = expandedRows.has(idx);
            const hasMismatches = line.mismatch_fields?.length > 0;

            return (
              <>
                <tr
                  key={idx}
                  className={clsx(
                    "border-t border-gray-100 transition-colors",
                    style.bg,
                    hasMismatches && "cursor-pointer hover:brightness-95"
                  )}
                  onClick={() => hasMismatches && toggleRow(idx)}
                >
                  {/* Ref + designation */}
                  <td className="px-4 py-3">
                    <p className="font-mono font-semibold text-gray-900 text-xs">
                      {line.ref_produit || "—"}
                    </p>
                    {line.designation && (
                      <p className="text-gray-500 text-xs truncate max-w-[200px]" title={line.designation}>
                        {line.designation}
                      </p>
                    )}
                    {line.confidence < 0.70 && (
                      <ConfidenceIndicator value={line.confidence} />
                    )}
                  </td>

                  {/* BC cols */}
                  <td className={clsx("text-right px-3 py-3 border-l border-gray-200", cellHighlight("qty_bc_vs_bl", line.mismatch_fields))}>
                    {formatQty(line.qty_bc)}
                  </td>
                  <td className={clsx("text-right px-3 py-3", cellHighlight("prix_unitaire", line.mismatch_fields))}>
                    {formatCurrency(line.prix_bc, "")}
                  </td>

                  {/* BL cols */}
                  <td className={clsx("text-right px-3 py-3 border-l border-gray-200", cellHighlight("qty_bc_vs_bl", line.mismatch_fields))}>
                    {formatQty(line.qty_bl)}
                  </td>

                  {/* FACTURE cols */}
                  <td className={clsx("text-right px-3 py-3 border-l border-gray-200", cellHighlight("qty_bc_vs_facture", line.mismatch_fields))}>
                    {formatQty(line.qty_facture)}
                  </td>
                  <td className={clsx("text-right px-3 py-3", cellHighlight("prix_unitaire", line.mismatch_fields))}>
                    {formatCurrency(line.prix_facture, "")}
                  </td>
                  <td className={clsx("text-right px-3 py-3", cellHighlight("tva_rate", line.mismatch_fields))}>
                    {line.tva_facture != null ? `${line.tva_facture}%` : "—"}
                  </td>

                  {/* Verdict */}
                  <td className="text-center px-4 py-3 border-l border-gray-200">
                    <LineVerdictBadge verdict={line.verdict} />
                  </td>

                  {/* Expand toggle */}
                  <td className="px-3 py-3 text-gray-400">
                    {hasMismatches && (
                      isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                    )}
                  </td>
                </tr>

                {/* Expanded mismatch detail row */}
                {isExpanded && hasMismatches && (
                  <tr key={`${idx}-detail`} className="bg-red-50 border-t border-red-100">
                    <td colSpan={9} className="px-6 py-3">
                      <p className="text-xs font-semibold text-red-700 mb-1">
                        Mismatched fields:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {line.mismatch_fields.map((f) => (
                          <span key={f} className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded font-mono">
                            {f}
                          </span>
                        ))}
                      </div>
                      {line.notes && (
                        <p className="text-xs text-red-600 mt-1">{line.notes}</p>
                      )}
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function cellHighlight(field, mismatches = []) {
  return mismatches.includes(field) ? "bg-red-100 font-bold text-red-800" : "";
}