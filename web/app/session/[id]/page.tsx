import { redirect } from "next/navigation";
import { auth } from "@/auth";
import VoiceSessionWithPresence from "@/app/components/VoiceSessionWithPresence";
import VoiceSession from "@/app/components/VoiceSession";

interface SessionPageProps {
  params: {
    id: string;
  };
}

export default async function SessionPage({ params }: SessionPageProps) {
  const session = await auth();

  if (!session?.user) {
    redirect("/auth/signin");
  }

  return (
    <div className="w-screen h-screen">
      <VoiceSessionWithPresence sessionId={params.id} role="operator">
        <div className="max-w-4xl mx-auto p-8">
          <VoiceSession />
        </div>
      </VoiceSessionWithPresence>
    </div>
  );
}
