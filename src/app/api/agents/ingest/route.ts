import { NextRequest, NextResponse } from 'next/server';
import { parseExcelFile, upsertInvoices } from '@/agents/ingestion';

export async function POST(req: NextRequest) {
  const authHeader = req.headers.get('x-agent-secret');
  if (authHeader !== process.env.AGENT_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const formData = await req.formData();
    const file = formData.get('file') as File;
    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 });
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const rows = await parseExcelFile(buffer);
    const result = await upsertInvoices(rows);

    return NextResponse.json({ success: true, rows_parsed: rows.length, ...result });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
