import { NextRequest, NextResponse } from 'next/server';
import { runAgingAgent } from '@/agents/aging';

export async function POST(req: NextRequest) {
  const authHeader = req.headers.get('x-agent-secret');
  if (authHeader !== process.env.AGENT_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const result = await runAgingAgent();
    return NextResponse.json({ success: true, ...result });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
