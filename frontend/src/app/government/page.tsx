import type { Metadata } from "next";
import { GroupDirectoryPage } from "@/components/GroupDirectory";
import { groupByName } from "@/lib/explorer/categoryGroups";

// Shared explorer page; this group's categories live in lib/explorer/categoryGroups.ts.
const group = groupByName("government");

export const metadata: Metadata = { title: group.title, description: group.blurb, alternates: { canonical: group.path } };

export default function Page() {
  return <GroupDirectoryPage name="government" />;
}
