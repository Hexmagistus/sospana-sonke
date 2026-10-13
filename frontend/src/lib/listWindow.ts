/** How many stored roles a public list paints on one page. */
export const LIST_PAGE = 10;

/** A non-negative page start. Anything else is the first page. */
export function listOffset(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 500) return 0;
  return parsed - (parsed % LIST_PAGE);
}
