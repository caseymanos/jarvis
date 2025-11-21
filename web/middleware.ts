import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Lightweight middleware - only check protected routes
export function middleware(request: NextRequest) {
  // For now, allow all requests
  // Auth will be handled by NextAuth on the page level
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Only run middleware on specific protected routes
    "/session/:path*",
  ],
};
