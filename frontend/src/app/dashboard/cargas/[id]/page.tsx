import { LoadDetail } from "@/features/dashboard/load-detail";

export default async function LoadDetailPage({ params }: PageProps<"/dashboard/cargas/[id]">) {
  const { id } = await params;
  return <LoadDetail id={id} />;
}
