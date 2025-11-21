import { redirect } from "next/navigation";
import { auth } from "@/auth";
import VoiceSessionWithPresence from "@/app/components/VoiceSessionWithPresence";

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
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Voice Session
            </h1>
            <div className="space-y-4">
              <div>
                <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Session ID
                </h2>
                <div className="font-mono text-sm bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded">
                  {params.id}
                </div>
              </div>

              <div>
                <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Instructions
                </h2>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
                  <li>• Move your cursor to see collaborative pointers</li>
                  <li>• Watch for join/leave notifications in the top-right</li>
                  <li>• Check the network status pill in the top-left</li>
                  <li>• View active users in the presence list</li>
                </ul>
              </div>

              <div>
                <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Role Badges
                </h2>
                <div className="flex gap-2">
                  <span className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium">
                    SUP - Supervisor
                  </span>
                  <span className="text-xs px-2 py-1 rounded bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 font-medium">
                    OBS - Observer
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </VoiceSessionWithPresence>
    </div>
  );
}
