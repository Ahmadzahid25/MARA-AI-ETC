import { Chip, Typography } from '@openhands/ui';
import type { PolicyCitation } from '../../types/knowledge';
import { isProvisional } from '../../types/knowledge';

interface PolicyCitationRendererProps {
  citation: PolicyCitation | null;
}

export function PolicyCitationRenderer({ citation }: PolicyCitationRendererProps) {
  if (!citation) {
    return (
      <Typography.Text fontSize="xs" className="italic text-slate-400 dark:text-slate-500">
        No policy citation available
      </Typography.Text>
    );
  }

  const provisional = isProvisional(citation);

  return (
    <div className="mt-2 space-y-1.5 border-t border-gray-100 pt-2 dark:border-[#222328]">
      <div className="flex items-center gap-1.5">
        <Chip color={provisional ? 'primaryDark' : 'green'} variant="pill">
          {citation.trust_tier}
        </Chip>
        <Typography.Text fontSize="xxs" className="font-mono text-slate-500 dark:text-slate-400">
          {citation.document_id} v{citation.version}
        </Typography.Text>
        <Typography.Text fontSize="xxs" className="text-slate-400 dark:text-slate-500">
          {citation.locator}
        </Typography.Text>
        {citation.relevance != null && (
          <Typography.Text fontSize="xxs" className="text-slate-400 dark:text-slate-500">
            relevance: {(citation.relevance * 100).toFixed(0)}%
          </Typography.Text>
        )}
      </div>

      {citation.superseded_on && (
        <Typography.Text fontSize="xs" className="text-amber-600 dark:text-amber-400">
          Cited policy has since been superseded (version from {citation.superseded_on})
        </Typography.Text>
      )}

      {provisional && (
        <Typography.Text fontSize="xs" className="text-amber-600 dark:text-amber-400">
          Source not yet reviewed by a Knowledge Owner
        </Typography.Text>
      )}
    </div>
  );
}
