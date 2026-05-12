import { FileText, Calendar, User, Zap, AlertTriangle } from "lucide-react";
import ConfidenceIndicator from "./ConfidenceIndicator";
import {
  formatDate,
  formatCurrency,
  formatExtractionTier,
} from "../../utils/formatters";
import clsx from "clsx";

const DOC_TYPE_LABELS = {
  BC: "Bon de Commande",
  BL: "Bon de Livraison",
  FACTURE: "Facture",
};

const DOC_TYPE_COLORS = {
  BC: "border-blue-400 bg-blue-50",
  BL: "border-teal-400 bg-teal-50",
  FACTURE: "border-violet-400 bg-violet-50",
};

export default function DocumentSummary({ document }) {
  const { doc_type, ref_document, document_date, supplier_name,
    extraction_confidence, extraction_source_tier,
    has_low_confidence_fields, total_ht, total_ttc,
    field_confidence_map, lines } = document;

  return (
    <div className={clsx("border-l-4 rounded-lg p-5 bg-white shadow-sm", DOC_TYPE_COLORS[doc_type])}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-gray-500" />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              {DOC_TYPE_LABELS[doc_type] || doc_type}
            </span>
          </div>
          <p className="mt-1 font-mono font-bold text-gray-900 text-lg">
            {ref_document || "No reference"}
          </p>
        </div>

        <div className="text-right shrink-0">
          <p className="text-xs text-gray-400 mb-1">Extraction confidence</p>
          <ConfidenceIndicator value={extraction_confidence} />
          {has_low_confidence_fields && (
            <div className="flex items-center justify-end gap-1 mt-1 text-xs text-yellow-600">
              <AlertTriangle size={11} />
              <span>Low confidence fields</span>
            </div>
          )}
        </div>
      </div>

      {/* Metadata grid */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <MetaRow icon={Calendar} label="Date" value={formatDate(document_date)} />
        <MetaRow icon={User} label="Supplier" value={supplier_name || "—"} />
        <MetaRow
          icon={Zap}
          label="Extraction"
          value={formatExtractionTier(extraction_source_tier)}
        />
        <MetaRow label="Lines" value={`${lines?.length || 0} items`} />

        {total_ht !== null && total_ht !== undefined && (
          <MetaRow label="Total HT" value={formatCurrency(total_ht)} />
        )}
        {total_ttc !== null && total_ttc !== undefined && (
          <MetaRow label="Total TTC" value={formatCurrency(total_ttc)} />
        )}
      </div>

      {/* Per-field confidence warnings */}
      {field_confidence_map && Object.keys(field_confidence_map).length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-500 mb-2">Field confidence</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(field_confidence_map).map(([field, conf]) => (
              <div key={field} className="flex items-center gap-1 bg-gray-50 rounded px-2 py-1">
                <span className="text-xs text-gray-600">{field}</span>
                <ConfidenceIndicator value={conf} showIcon={conf < 0.70} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetaRow({ icon: Icon, label, value }) {
  return (
    <div>
      <div className="flex items-center gap-1 text-xs text-gray-400 mb-0.5">
        {Icon && <Icon size={11} />}
        {label}
      </div>
      <p className="text-sm text-gray-800 font-medium truncate" title={value}>
        {value}
      </p>
    </div>
  );
}