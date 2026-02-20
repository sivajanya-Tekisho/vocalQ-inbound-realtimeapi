-- ============================================
-- VocalQ Complete Database Schema
-- ============================================

-- Enable required extensions
create extension if not exists "uuid-ossp";

-- ============================================
-- 1. CALLS TABLE
-- Stores all inbound/outbound call records
-- ============================================
create table public.calls (
    call_id uuid primary key default uuid_generate_v4(),
    caller_number text,
    start_time timestamptz default now(),
    end_time timestamptz,
    call_duration integer,
    language text default 'en-US',
    intent text,
    call_status text default 'active',
    summary text,
    transcript jsonb default '[]',
    sentiment text,
    token_usage integer,
    created_at timestamptz default now()
);

-- ============================================
-- 2. CALL SUMMARIES TABLE
-- Stores AI-generated summaries for calls
-- ============================================
create table public.call_summaries (
    id uuid primary key default uuid_generate_v4(),
    call_id uuid references public.calls(call_id) on delete cascade,
    summary_text text,
    created_at timestamptz default now()
);

-- ============================================
-- 3. CALL QUEUE TABLE
-- Manages call priority and assignment
-- ============================================
create table public.call_queue (
    id uuid primary key default uuid_generate_v4(),
    call_id uuid references public.calls(call_id) on delete cascade,
    caller_number text not null,
    priority integer default 0, -- 0=normal, 1=high, 2=urgent
    status text default 'waiting', -- waiting, assigned, completed, cancelled
    assigned_to text, -- user/agent ID (for future auth)
    queue_position integer,
    created_at timestamptz default now(),
    assigned_at timestamptz,
    completed_at timestamptz
);

-- ============================================
-- 4. KNOWLEDGE BASE DOCUMENTS TABLE
-- Tracks uploaded documents with user info
-- ============================================
create table public.knowledge_base_documents (
    id uuid primary key default uuid_generate_v4(),
    doc_id text unique not null, -- matches folder name in storage
    filename text not null,
    file_size bigint,
    file_type text, -- pdf, txt, docx
    upload_date timestamptz default now(),
    uploaded_by text, -- user ID/email (for future auth)
    chunk_count integer default 0,
    vector_count integer default 0,
    status text default 'processing', -- processing, ready, failed
    metadata jsonb default '{}',
    created_at timestamptz default now()
);

-- ============================================
-- INDEXES for performance
-- ============================================

-- Calls indexes
create index idx_calls_status on public.calls(call_status);
create index idx_calls_start_time on public.calls(start_time desc);
create index idx_calls_created_at on public.calls(created_at desc);
create index idx_calls_caller on public.calls(caller_number);

-- Call summaries index
create index idx_call_summaries_call_id on public.call_summaries(call_id);

-- Queue indexes
create index idx_queue_status on public.call_queue(status);
create index idx_queue_priority on public.call_queue(priority desc);
create index idx_queue_created on public.call_queue(created_at);
create index idx_queue_assigned_to on public.call_queue(assigned_to);

-- Knowledge base indexes
create index idx_kb_doc_id on public.knowledge_base_documents(doc_id);
create index idx_kb_uploaded_by on public.knowledge_base_documents(uploaded_by);
create index idx_kb_status on public.knowledge_base_documents(status);
create index idx_kb_upload_date on public.knowledge_base_documents(upload_date desc);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
alter table public.calls enable row level security;
alter table public.call_summaries enable row level security;
alter table public.call_queue enable row level security;
alter table public.knowledge_base_documents enable row level security;

-- Allow all access for now (update when auth is implemented)
create policy "Enable all access for anon" on public.calls 
    for all using (true) with check (true);

create policy "Enable all access for anon" on public.call_summaries 
    for all using (true) with check (true);

create policy "Enable all access for anon" on public.call_queue 
    for all using (true) with check (true);

create policy "Enable all access for anon" on public.knowledge_base_documents 
    for all using (true) with check (true);

-- ============================================
-- FUNCTIONS for queue management
-- ============================================

-- Function to auto-assign queue position
create or replace function assign_queue_position()
returns trigger as $$
begin
    if new.queue_position is null then
        select coalesce(max(queue_position), 0) + 1
        into new.queue_position
        from public.call_queue
        where status = 'waiting';
    end if;
    return new;
end;
$$ language plpgsql;

-- Trigger to auto-assign position
create trigger set_queue_position
    before insert on public.call_queue
    for each row
    execute function assign_queue_position();
