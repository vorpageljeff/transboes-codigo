import { TripDetail } from "@/features/dashboard/trip-detail";

export default async function TripDetailPage({ params }: PageProps<"/dashboard/viagens/[id]">) {
  const { id } = await params;
  return <TripDetail id={id} />;
}
