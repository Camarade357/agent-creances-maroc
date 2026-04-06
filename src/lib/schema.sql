-- Clients
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255),
  phone VARCHAR(50),
  address TEXT,
  city VARCHAR(100),
  country VARCHAR(10) DEFAULT 'MA',
  annual_revenue DECIMAL(15,2),
  segment_id VARCHAR(50),
  payment_behavior VARCHAR(20) DEFAULT 'unknown',
  is_large_account BOOLEAN DEFAULT false,
  is_good_payer BOOLEAN DEFAULT true,
  avg_days_to_pay DECIMAL(5,1),
  total_outstanding DECIMAL(15,2) DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Invoices
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id VARCHAR(100) UNIQUE NOT NULL,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  invoice_number VARCHAR(100) NOT NULL,
  amount_ht DECIMAL(15,2) NOT NULL,
  amount_ttc DECIMAL(15,2) NOT NULL,
  currency VARCHAR(10) DEFAULT 'MAD',
  issue_date DATE NOT NULL,
  due_date DATE NOT NULL,
  payment_term_days INTEGER DEFAULT 60,
  status VARCHAR(30) DEFAULT 'pending',
  days_overdue INTEGER DEFAULT 0,
  bucket VARCHAR(20),
  aging_risk VARCHAR(20),
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  amount DECIMAL(15,2) NOT NULL,
  payment_date DATE NOT NULL,
  reference VARCHAR(100),
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relance history
CREATE TABLE relance_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  relance_type VARCHAR(50) NOT NULL,
  tone VARCHAR(30),
  days_overdue_at_relance INTEGER,
  email_subject TEXT,
  email_body TEXT,
  sent_at TIMESTAMP WITH TIME ZONE,
  approved_by VARCHAR(100),
  status VARCHAR(20) DEFAULT 'draft',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Aging snapshots (weekly)
CREATE TABLE aging_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_date DATE NOT NULL,
  total_outstanding DECIMAL(15,2),
  bucket_0_30 DECIMAL(15,2) DEFAULT 0,
  bucket_31_60 DECIMAL(15,2) DEFAULT 0,
  bucket_61_90 DECIMAL(15,2) DEFAULT 0,
  bucket_90_plus DECIMAL(15,2) DEFAULT 0,
  nb_clients_overdue INTEGER DEFAULT 0,
  nb_invoices_overdue INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_invoices_client_id ON invoices(client_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_relance_client_id ON relance_history(client_id);
