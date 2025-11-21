import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

/**
 * POST /api/transcripts/bulk-delete
 *
 * Hard-delete multiple transcript chunks with GDPR compliance.
 * Deletion must complete within 1 second per chunk.
 */
export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    // Authenticate user
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { chunkIds } = body;

    if (!Array.isArray(chunkIds) || chunkIds.length === 0) {
      return NextResponse.json(
        { error: 'chunkIds must be a non-empty array' },
        { status: 400 }
      );
    }

    // Verify all chunks belong to user
    const chunks = await prisma.transcriptChunk.findMany({
      where: {
        id: { in: chunkIds },
      },
      include: {
        session: true,
      },
    });

    // Check ownership
    const unauthorizedChunks = chunks.filter(
      chunk => chunk.session.userId !== session.user.id
    );

    if (unauthorizedChunks.length > 0) {
      return NextResponse.json(
        {
          error: 'Forbidden: Some transcript chunks do not belong to you',
          unauthorizedIds: unauthorizedChunks.map(c => c.id),
        },
        { status: 403 }
      );
    }

    // Hard delete all chunks (GDPR compliance)
    const result = await prisma.transcriptChunk.deleteMany({
      where: {
        id: { in: chunkIds },
      },
    });

    const deletionTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      deletedCount: result.count,
      deletionTime,
      message: `${result.count} transcript chunks permanently deleted`,
    });

  } catch (error) {
    console.error('Error bulk deleting transcript chunks:', error);
    return NextResponse.json(
      { error: 'Failed to bulk delete transcript chunks' },
      { status: 500 }
    );
  }
}
