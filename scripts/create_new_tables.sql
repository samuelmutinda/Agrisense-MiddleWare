-- AgriSense Middleware Integration Migration
-- New tables for AgriSenseApp frontend integration
-- Run with: psql -U your_user -d your_database -f create_new_tables.sql

BEGIN;

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    organization_type VARCHAR(20) NOT NULL CHECK (organization_type IN ('farm', 'processor', 'distributor', 'retailer', 'logistics', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'pending_verification')),
    tax_id VARCHAR(50),
    registration_number VARCHAR(50),
    primary_contact_name VARCHAR(100),
    primary_contact_email VARCHAR(100),
    primary_contact_phone VARCHAR(20),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    parent_organization_id UUID REFERENCES organizations(id),
    settings JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_organizations_tenant_id ON organizations(tenant_id);
CREATE INDEX IF NOT EXISTS ix_organizations_type ON organizations(organization_type);

-- Reefer Trucks table
CREATE TABLE IF NOT EXISTS reefer_trucks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    truck_number VARCHAR(50) NOT NULL,
    license_plate VARCHAR(20) NOT NULL,
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER,
    capacity_kg FLOAT,
    refrigeration_unit_model VARCHAR(100),
    min_temperature FLOAT,
    max_temperature FLOAT,
    status VARCHAR(20) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'in_transit', 'maintenance', 'out_of_service')),
    current_latitude FLOAT,
    current_longitude FLOAT,
    current_temperature FLOAT,
    last_location_update TIMESTAMPTZ,
    driver_id UUID REFERENCES users(id),
    current_manifest_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, truck_number),
    UNIQUE(tenant_id, license_plate)
);
CREATE INDEX IF NOT EXISTS ix_reefer_trucks_tenant_id ON reefer_trucks(tenant_id);
CREATE INDEX IF NOT EXISTS ix_reefer_trucks_status ON reefer_trucks(status);

-- Manifests table
CREATE TABLE IF NOT EXISTS manifests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    manifest_number VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'in_transit', 'delivered', 'cancelled')),
    truck_id UUID REFERENCES reefer_trucks(id),
    driver_id UUID REFERENCES users(id),
    origin_facility_id UUID REFERENCES cold_storage_units(id),
    destination_facility_id UUID REFERENCES cold_storage_units(id),
    customer_id UUID REFERENCES customers(id),
    scheduled_departure TIMESTAMPTZ,
    actual_departure TIMESTAMPTZ,
    scheduled_arrival TIMESTAMPTZ,
    actual_arrival TIMESTAMPTZ,
    total_weight_kg FLOAT,
    total_items INTEGER DEFAULT 0,
    special_instructions TEXT,
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, manifest_number)
);
CREATE INDEX IF NOT EXISTS ix_manifests_tenant_id ON manifests(tenant_id);
CREATE INDEX IF NOT EXISTS ix_manifests_status ON manifests(status);

-- Manifest Items table
CREATE TABLE IF NOT EXISTS manifest_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manifest_id UUID NOT NULL REFERENCES manifests(id) ON DELETE CASCADE,
    batch_id UUID,
    crop_id UUID REFERENCES crops(id),
    description VARCHAR(255),
    quantity FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    weight_kg FLOAT,
    temperature_requirement FLOAT,
    handling_instructions TEXT,
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS ix_manifest_items_manifest_id ON manifest_items(manifest_id);

-- Produce Batches table
CREATE TABLE IF NOT EXISTS produce_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    batch_number VARCHAR(50) NOT NULL,
    crop_id UUID NOT NULL REFERENCES crops(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_storage', 'in_transit', 'delivered', 'spoiled', 'rejected')),
    quality_grade VARCHAR(10) CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'rejected')),
    quantity FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    weight_kg FLOAT,
    harvest_date DATE,
    production_date DATE,
    expiry_date DATE,
    farm_id UUID,
    source_customer_id UUID REFERENCES customers(id),
    current_storage_unit_id UUID REFERENCES cold_storage_units(id),
    current_temperature FLOAT,
    target_temperature FLOAT,
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, batch_number)
);
CREATE INDEX IF NOT EXISTS ix_produce_batches_tenant_id ON produce_batches(tenant_id);
CREATE INDEX IF NOT EXISTS ix_produce_batches_status ON produce_batches(status);

-- Inventory Movements table
CREATE TABLE IF NOT EXISTS inventory_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('inbound', 'outbound', 'transfer', 'adjustment', 'loss', 'spoilage')),
    batch_id UUID REFERENCES produce_batches(id),
    from_location_id UUID REFERENCES cold_storage_units(id),
    to_location_id UUID REFERENCES cold_storage_units(id),
    quantity FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    reason VARCHAR(255),
    reference_type VARCHAR(50),
    reference_id UUID,
    performed_by_id UUID REFERENCES users(id),
    performed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_inventory_movements_tenant_id ON inventory_movements(tenant_id);
CREATE INDEX IF NOT EXISTS ix_inventory_movements_batch_id ON inventory_movements(batch_id);

-- Inspections table
CREATE TABLE IF NOT EXISTS inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    inspection_type VARCHAR(20) NOT NULL CHECK (inspection_type IN ('arrival', 'quality', 'storage', 'dispatch', 'regulatory')),
    result VARCHAR(20) NOT NULL CHECK (result IN ('pass', 'fail', 'conditional', 'pending')),
    batch_id UUID REFERENCES produce_batches(id),
    storage_unit_id UUID REFERENCES cold_storage_units(id),
    inspector_id UUID REFERENCES users(id),
    inspection_date TIMESTAMPTZ NOT NULL,
    criteria JSONB,
    overall_score FLOAT,
    notes TEXT,
    images TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_inspections_tenant_id ON inspections(tenant_id);
CREATE INDEX IF NOT EXISTS ix_inspections_batch_id ON inspections(batch_id);

-- Certifications table
CREATE TABLE IF NOT EXISTS certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    certification_type VARCHAR(30) NOT NULL CHECK (certification_type IN ('organic', 'haccp', 'iso22000', 'globalgap', 'fair_trade', 'halal', 'kosher', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'suspended', 'pending_renewal')),
    certificate_number VARCHAR(100) NOT NULL,
    issued_by VARCHAR(100) NOT NULL,
    issued_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    scope TEXT,
    document_url VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_certifications_tenant_id ON certifications(tenant_id);
CREATE INDEX IF NOT EXISTS ix_certifications_status ON certifications(status);

-- Regulatory Compliance table
CREATE TABLE IF NOT EXISTS regulatory_compliance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    compliance_type VARCHAR(30) NOT NULL CHECK (compliance_type IN ('food_safety', 'environmental', 'labor', 'transport', 'import_export', 'tax', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'compliant' CHECK (status IN ('compliant', 'non_compliant', 'pending_review', 'under_investigation')),
    regulation_name VARCHAR(255) NOT NULL,
    authority VARCHAR(100) NOT NULL,
    compliance_date DATE,
    next_review_date DATE,
    findings TEXT,
    corrective_actions TEXT,
    document_urls TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_regulatory_compliance_tenant_id ON regulatory_compliance(tenant_id);
CREATE INDEX IF NOT EXISTS ix_regulatory_compliance_status ON regulatory_compliance(status);

-- Financial Transactions table
CREATE TABLE IF NOT EXISTS financial_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    transaction_number VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('sale', 'purchase', 'refund', 'adjustment', 'fee', 'commission')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'cancelled', 'refunded')),
    payment_method VARCHAR(20) CHECK (payment_method IN ('cash', 'mpesa', 'bank_transfer', 'credit', 'check', 'other')),
    amount FLOAT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'KES',
    customer_id UUID REFERENCES customers(id),
    invoice_id UUID REFERENCES invoices(id),
    manifest_id UUID REFERENCES manifests(id),
    reference_number VARCHAR(100),
    description TEXT,
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, transaction_number)
);
CREATE INDEX IF NOT EXISTS ix_financial_transactions_tenant_id ON financial_transactions(tenant_id);
CREATE INDEX IF NOT EXISTS ix_financial_transactions_customer_id ON financial_transactions(customer_id);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'paid', 'partially_paid', 'overdue', 'cancelled')),
    customer_id UUID NOT NULL REFERENCES customers(id),
    manifest_id UUID REFERENCES manifests(id),
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal FLOAT NOT NULL DEFAULT 0,
    tax_amount FLOAT DEFAULT 0,
    discount_amount FLOAT DEFAULT 0,
    total_amount FLOAT NOT NULL DEFAULT 0,
    amount_paid FLOAT DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'KES',
    line_items JSONB,
    notes TEXT,
    terms TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, invoice_number)
);
CREATE INDEX IF NOT EXISTS ix_invoices_tenant_id ON invoices(tenant_id);
CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS ix_invoices_customer_id ON invoices(customer_id);

-- Update financial_transactions FK to invoices (deferred creation)
ALTER TABLE financial_transactions DROP CONSTRAINT IF EXISTS financial_transactions_invoice_id_fkey;
ALTER TABLE financial_transactions ADD CONSTRAINT financial_transactions_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES invoices(id);

-- KPI Metrics table
CREATE TABLE IF NOT EXISTS kpi_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN ('operations', 'financial', 'quality', 'efficiency', 'sustainability')),
    value FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    target_value FLOAT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    facility_id UUID REFERENCES cold_storage_units(id),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_kpi_metrics_tenant_id ON kpi_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS ix_kpi_metrics_category ON kpi_metrics(category);

-- GCP Profiles (Good Cold-chain Practice) table
CREATE TABLE IF NOT EXISTS gcp_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    facility_id UUID NOT NULL REFERENCES cold_storage_units(id),
    certification_level VARCHAR(10) NOT NULL CHECK (certification_level IN ('bronze', 'silver', 'gold', 'platinum')),
    temperature_compliance_score FLOAT NOT NULL,
    hygiene_score FLOAT NOT NULL,
    documentation_score FLOAT NOT NULL,
    training_score FLOAT NOT NULL,
    audit_date TIMESTAMPTZ NOT NULL,
    next_audit_date TIMESTAMPTZ,
    auditor_name VARCHAR(100),
    recommendations TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_gcp_profiles_tenant_id ON gcp_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS ix_gcp_profiles_facility_id ON gcp_profiles(facility_id);

-- Asset Performance table
CREATE TABLE IF NOT EXISTS asset_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL,
    asset_type VARCHAR(25) NOT NULL CHECK (asset_type IN ('refrigeration_unit', 'cold_room', 'reefer_truck', 'conveyor', 'packaging_machine', 'forklift')),
    asset_name VARCHAR(100) NOT NULL,
    uptime_percent FLOAT NOT NULL,
    efficiency_score FLOAT NOT NULL,
    performance_status VARCHAR(15) NOT NULL CHECK (performance_status IN ('optimal', 'degraded', 'critical', 'offline')),
    measurement_timestamp TIMESTAMPTZ NOT NULL,
    energy_consumption_kwh FLOAT,
    operating_hours FLOAT,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_maintenance TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_asset_performance_tenant_id ON asset_performance(tenant_id);
CREATE INDEX IF NOT EXISTS ix_asset_performance_asset_id ON asset_performance(asset_id);

-- Energy Consumption table
CREATE TABLE IF NOT EXISTS energy_consumption (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    facility_id UUID NOT NULL REFERENCES cold_storage_units(id),
    period_date DATE NOT NULL,
    total_kwh FLOAT NOT NULL,
    refrigeration_kwh FLOAT,
    lighting_kwh FLOAT,
    other_kwh FLOAT,
    peak_demand_kw FLOAT,
    energy_source VARCHAR(15) NOT NULL CHECK (energy_source IN ('grid', 'solar', 'generator', 'hybrid')),
    cost_per_kwh FLOAT,
    total_cost FLOAT,
    carbon_footprint_kg FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_energy_consumption_tenant_id ON energy_consumption(tenant_id);
CREATE INDEX IF NOT EXISTS ix_energy_consumption_facility_id ON energy_consumption(facility_id);

-- Operating Costs table
CREATE TABLE IF NOT EXISTS operating_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    facility_id UUID REFERENCES cold_storage_units(id),
    category VARCHAR(15) NOT NULL CHECK (category IN ('energy', 'labor', 'maintenance', 'supplies', 'insurance', 'rent', 'transport', 'other')),
    description VARCHAR(255) NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'KES',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    vendor_name VARCHAR(100),
    invoice_reference VARCHAR(50),
    is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_operating_costs_tenant_id ON operating_costs(tenant_id);
CREATE INDEX IF NOT EXISTS ix_operating_costs_category ON operating_costs(category);

-- Maintenance Records table
CREATE TABLE IF NOT EXISTS maintenance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    maintenance_type VARCHAR(15) NOT NULL CHECK (maintenance_type IN ('preventive', 'corrective', 'emergency', 'calibration')),
    status VARCHAR(15) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    scheduled_date TIMESTAMPTZ NOT NULL,
    completed_date TIMESTAMPTZ,
    description VARCHAR(500) NOT NULL,
    assigned_technician_id UUID REFERENCES users(id),
    estimated_duration_hours FLOAT,
    actual_duration_hours FLOAT,
    estimated_cost FLOAT,
    actual_cost FLOAT,
    parts_required TEXT[],
    parts_used TEXT[],
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_maintenance_records_tenant_id ON maintenance_records(tenant_id);
CREATE INDEX IF NOT EXISTS ix_maintenance_records_asset_id ON maintenance_records(asset_id);
CREATE INDEX IF NOT EXISTS ix_maintenance_records_status ON maintenance_records(status);

-- Staff Operations table
CREATE TABLE IF NOT EXISTS staff_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    staff_id UUID NOT NULL REFERENCES users(id),
    operation_type VARCHAR(15) NOT NULL CHECK (operation_type IN ('shift', 'task', 'training', 'overtime')),
    facility_id UUID REFERENCES cold_storage_units(id),
    shift_type VARCHAR(15) CHECK (shift_type IN ('morning', 'afternoon', 'night', 'rotating')),
    operation_date DATE NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    task_description VARCHAR(500),
    area_assigned VARCHAR(100),
    supervisor_id UUID REFERENCES users(id),
    performance_notes TEXT,
    productivity_score FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_staff_operations_tenant_id ON staff_operations(tenant_id);
CREATE INDEX IF NOT EXISTS ix_staff_operations_staff_id ON staff_operations(staff_id);
CREATE INDEX IF NOT EXISTS ix_staff_operations_date ON staff_operations(operation_date);

-- Audit Trail table
CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(15) NOT NULL CHECK (action IN ('create', 'update', 'delete', 'login', 'logout', 'export', 'import', 'approve', 'reject')),
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    resource_name VARCHAR(255),
    changes JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS ix_audit_trail_tenant_id ON audit_trail(tenant_id);
CREATE INDEX IF NOT EXISTS ix_audit_trail_user_id ON audit_trail(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_trail_timestamp ON audit_trail(timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_trail_resource_type ON audit_trail(resource_type);
CREATE INDEX IF NOT EXISTS ix_audit_trail_resource_id ON audit_trail(resource_id);

COMMIT;

-- Summary: Created 19 new tables for AgriSenseApp integration
-- 1. organizations - Multi-tenant organization management
-- 2. reefer_trucks - Refrigerated truck fleet management
-- 3. manifests - Shipping manifest tracking
-- 4. manifest_items - Line items for manifests
-- 5. produce_batches - Batch tracking with quality grades
-- 6. inventory_movements - Stock movement audit trail
-- 7. inspections - Quality and regulatory inspections
-- 8. certifications - Certification tracking (organic, HACCP, etc)
-- 9. regulatory_compliance - Compliance status tracking
-- 10. financial_transactions - Payment and transaction records
-- 11. invoices - Invoice management
-- 12. kpi_metrics - Key performance indicator tracking
-- 13. gcp_profiles - Good Cold-chain Practice profiles
-- 14. asset_performance - Equipment performance monitoring
-- 15. energy_consumption - Energy usage tracking
-- 16. operating_costs - Operational expense tracking
-- 17. maintenance_records - Asset maintenance scheduling
-- 18. staff_operations - Staff shift and task tracking
-- 19. audit_trail - System-wide audit logging
