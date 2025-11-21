import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

/**
 * DELETE /api/transcripts/[chunkId]
 *
 * Hard-delete a transcript chunk with GDPR compliance.
 * Deletion must complete within 1 second.
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ chunkId: string }> }
) {
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

    const { chunkId } = await params;

    // Verify ownership and get chunk
    const chunk = await prisma.transcriptChunk.findUnique({
      where: { id: chunkId },
      include: {
        session: true,
      },
    });

    if (!chunk) {
      return NextResponse.json(
        { error: 'Transcript chunk not found' },
        { status: 404 }
      );
    }

    // Verify user owns the session
    if (chunk.session.userId !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden: You do not own this transcript' },
        { status: 403 }
      );
    }

    // Hard delete from database (GDPR compliance)
    await prisma.transcriptChunk.delete({
      where: { id: chunkId },
    });

    const deletionTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      chunkId,
      deletionTime,
      message: 'Transcript chunk permanently deleted',
    });

  } catch (error) {
    console.error('Error deleting transcript chunk:', error);
    return NextResponse.json(
      { error: 'Failed to delete transcript chunk' },
      { status: 500 }
    );
  }
}
