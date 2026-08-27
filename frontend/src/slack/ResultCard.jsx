// Renders the structured `records` the API returns as a Slack Block Kit-style
// card. Falls back to the plain `answer` text whenever there is no structure
// to show (parse errors, clarifications, empty results).

const LABELS = {
  source_id: "Source ID",
  gateway_id: "Gateway",
  line_type: "Line type",
  company_name: "Company",
  region: "Region",
  status: "Status",
  created_date: "Created",
  number: "Number",
  operator: "Operator",
  provisioned_date: "Provisioned",
  number_type: "Type",
  customer_id: "Customer ID",
  account_manager: "Account manager",
  ticket_id: "Ticket",
  subject: "Subject",
  priority: "Priority",
  primary_gateway: "Primary gateway",
  host: "Host",
  port: "Port",
};

const STATUS_STYLES = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  resolved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  suspended: "bg-amber-50 text-amber-700 ring-amber-200",
  in_progress: "bg-sky-50 text-sky-700 ring-sky-200",
  open: "bg-rose-50 text-rose-700 ring-rose-200",
  inactive: "bg-slate-100 text-slate-600 ring-slate-200",
};

const PRIORITY_STYLES = {
  high: "bg-rose-50 text-rose-700 ring-rose-200",
  medium: "bg-amber-50 text-amber-700 ring-amber-200",
  low: "bg-slate-100 text-slate-600 ring-slate-200",
};

function label(key) {
  return LABELS[key] ?? key.replace(/_/g, " ");
}

function prettyStatus(value) {
  return String(value).replace(/_/g, " ");
}

export function Pill({ value, kind = "status" }) {
  const table = kind === "priority" ? PRIORITY_STYLES : STATUS_STYLES;
  const style = table[String(value).toLowerCase()] ?? "bg-slate-100 text-slate-600 ring-slate-200";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${style}`}
    >
      {prettyStatus(value)}
    </span>
  );
}

function titleFor(record, entityType) {
  if (record.ticket_id) return `Ticket ${record.ticket_id}`;
  if (record.customer_id) return `Customer ${record.customer_id}`;
  if (record.source_id) return `Source ${record.source_id}`;
  if (entityType === "gateway" || entityType === "company") {
    return `Gateway ${record.gateway_id}`;
  }
  if (record.number) return record.number;
  if (record.gateway_id) return `Gateway ${record.gateway_id}`;
  return "Record";
}

function subtitleFor(record) {
  return record.subject || record.company_name || "";
}

/** One record shown as a field grid — the Slack "section with fields" look. */
function DetailCard({ record, entityType }) {
  // Anything already rendered in the header would otherwise appear twice.
  const skip = new Set(["status", "priority", "subject"]);
  const title = titleFor(record, entityType);
  const subtitle = subtitleFor(record);

  for (const [key, value] of Object.entries(record)) {
    const shown = String(value);
    if (title.endsWith(shown) || (subtitle && subtitle === shown)) skip.add(key);
  }

  const fields = Object.entries(record).filter(
    ([key, value]) => value !== "" && value != null && !skip.has(key)
  );

  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
      <div className="border-l-4 border-[#1264A3] px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-bold text-slate-900">{title}</span>
          {record.status && <Pill value={record.status} />}
          {record.priority && <Pill value={record.priority} kind="priority" />}
        </div>

        {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}

        <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
          {fields.map(([key, value]) => (
            <div key={key} className="min-w-0">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                {label(key)}
              </dt>
              <dd className="truncate text-sm text-slate-800">{String(value)}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

/** Many records shown as a compact table. */
function ListCard({ records, entityType, source }) {
  const shown = records.slice(0, 8);
  const remaining = records.length - shown.length;

  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2">
        <span className="text-sm font-semibold text-slate-700">
          {records.length} {records.length === 1 ? "record" : "records"}
        </span>
        <span className="font-mono text-xs text-slate-400">{source}</span>
      </div>

      <div className="divide-y divide-slate-100">
        {shown.map((record, index) => (
          <div
            key={index}
            className="flex items-center justify-between gap-3 px-4 py-2 hover:bg-slate-50"
          >
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-slate-800">
                {titleFor(record, entityType)}
              </div>
              {subtitleFor(record) && (
                <div className="truncate text-xs text-slate-500">
                  {subtitleFor(record)}
                </div>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {record.operator && (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                  {record.operator}
                </span>
              )}
              {record.priority && <Pill value={record.priority} kind="priority" />}
              {record.status && <Pill value={record.status} />}
            </div>
          </div>
        ))}
      </div>

      {remaining > 0 && (
        <div className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
          + {remaining} more
        </div>
      )}
    </div>
  );
}

export default function ResultCard({ answer, records, entityType, action, source }) {
  const hasRecords = Array.isArray(records) && records.length > 0;

  // No structure to render — a clarification, an error, or an empty result.
  if (!hasRecords) {
    return <p className="whitespace-pre-wrap text-[15px] text-slate-800">{answer}</p>;
  }

  const isList = action === "list" || records.length > 1;

  const summary = summaryLine(answer, isList);

  return (
    <div className="space-y-2">
      {summary && <p className="text-[15px] text-slate-800">{summary}</p>}
      {isList ? (
        <ListCard records={records} entityType={entityType} source={source} />
      ) : (
        <DetailCard record={records[0]} entityType={entityType} />
      )}
    </div>
  );
}

/**
 * The deterministic formatter already prints every field as text, which would
 * duplicate the card rendered underneath it. Strip that back to a single line,
 * or to nothing when the whole answer is just a record dump.
 *
 * An LLM-generated answer is prose rather than a dump, so it is kept as-is.
 */
function summaryLine(answer, isList) {
  const lines = answer.split("\n");

  if (isList) {
    return lines[0].replace(/:$/, "");
  }

  // "  Gateway ID: 470\n  Company: ..." — the formatter's full-record output.
  const isRecordDump = lines.length > 1 && /^\s{2}\S/.test(lines[0]);
  if (isRecordDump) return "";

  return lines[0];
}
