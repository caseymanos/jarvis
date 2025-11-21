"use client";

import { motion } from 'framer-motion';

interface UserPresence {
  user_id: string;
  call_sign: string;
  role: string;
  color: string;
  last_active: string;
}

interface UserPresenceListProps {
  users: UserPresence[];
  yourUserId?: string;
}

export default function UserPresenceList({ users, yourUserId }: UserPresenceListProps) {
  if (users.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 z-40 min-w-[200px]">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
        Session Participants ({users.length})
      </h3>

      <div className="space-y-2">
        {users.map((user) => {
          const isYou = user.user_id === yourUserId;

          return (
            <motion.div
              key={user.user_id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex items-center gap-2 text-sm"
            >
              {/* Color indicator */}
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: user.color }}
              />

              {/* Call sign */}
              <span className="text-gray-900 dark:text-gray-100 font-medium flex-1 truncate">
                {user.call_sign}
                {isYou && (
                  <span className="ml-1 text-gray-500 dark:text-gray-400 text-xs">
                    (you)
                  </span>
                )}
              </span>

              {/* Role badge */}
              {user.role === 'supervisor' && (
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200">
                  SUP
                </span>
              )}
              {user.role === 'observer' && (
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                  OBS
                </span>
              )}
              {user.role === 'operator' && (
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200">
                  OPR
                </span>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Activity indicator */}
      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span>Live collaboration</span>
        </div>
      </div>
    </div>
  );
}
