import { Chip, Typography } from '@openhands/ui';
import type { RetrievalResult } from '../../types/knowledge';
import { needsFreshSearch, hasAnyWithheld } from '../../types/knowledge';

interface RetrievalSummaryProps {
  result: RetrievalResult | null;
}

export function RetrievalSummary({ result }: RetrievalSummaryProps) {
  if (!result) return null;
  if (!result.no_confident_match && !hasAnyWithheld(result) && !needsFreshSearch(result)) return null;

  return (
    <div className="space-y-2 rounded-md border border-gray-200 bg-slate-50 p-3 dark:border-[#222328] dark:bg-[#18191C]">
      <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-white">
        Policy Search Results
      </Typography.Text>

      {result.no_confident_match && (
        <div className="rounded-md bg-amber-50 p-2 dark:bg-amber-950/30">
          <Typography.Text fontSize="xs" className="text-amber-800 dark:text-amber-200">
            No confident match found in the policy corpus.
          </Typography.Text>
        </div>
      )}

      {result.withheld_below_threshold > 0 && (
        <div className="flex items-center gap-2">
          <Chip color="gray" variant="pill">{result.withheld_below_threshold} withheld</Chip>
          <Typography.Text fontSize="xs" className="text-slate-500 dark:text-slate-400">
            Candidates scored below the relevance threshold — the corpus is weak on this question
          </Typography.Text>
        </div>
      )}

      {result.withheld_unverified > 0 && (
        <div className="flex items-center gap-2">
          <Chip color="primaryDark" variant="pill">{result.withheld_unverified} unverified</Chip>
          <Typography.Text fontSize="xs" className="text-slate-500 dark:text-slate-400">
            Content exists but no Knowledge Owner has approved it — chase the approval, this is not a gap in the corpus
          </Typography.Text>
        </div>
      )}

      {result.withheld_expired > 0 && (
        <div className="flex items-center gap-2">
          <Chip color="gray" variant="pill">{result.withheld_expired} expired</Chip>
          <Typography.Text fontSize="xs" className="text-slate-500 dark:text-slate-400">
            Cached market data aged out (90 day window) — a fresh search is the correct next step
          </Typography.Text>
        </div>
      )}

      {needsFreshSearch(result) && (
        <div className="rounded-md bg-blue-50 p-2 dark:bg-blue-950/30">
          <Typography.Text fontSize="xs" className="text-blue-700 dark:text-blue-300">
            All cached results have expired. A fresh search will be triggered automatically.
          </Typography.Text>
        </div>
      )}
    </div>
  );
}
