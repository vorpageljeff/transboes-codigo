import { DriverTracking } from "@/features/tracking/driver-tracking";

export default async function TrackingPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <DriverTracking token={token} />;
}
