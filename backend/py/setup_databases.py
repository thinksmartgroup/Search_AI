import os
import json
import sqlite3
import glob
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_DIR = "databases"
INDUSTRIES = ["chiropractic", "optometry", "auto_repair"]

def setup_database(industry):
    """Create and setup SQLite database for an industry"""
    os.makedirs(DB_DIR, exist_ok=True)
    db_path = os.path.join(DB_DIR, f"{industry}.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create vendors table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        website TEXT UNIQUE,
        description TEXT,
        products TEXT,
        is_primary_vendor BOOLEAN,
        confidence_score REAL,
        evidence TEXT,
        industry TEXT,
        source TEXT,
        platform_type TEXT,
        platform_score REAL,
        deployment_model TEXT,
        deployment_marking TEXT,
        deployment_characteristics TEXT,
        company_size TEXT,
        founding_year INTEGER,
        technology_stack TEXT,
        integration_capabilities TEXT,
        compliance_certifications TEXT,
        pricing_model TEXT,
        hosting_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_website ON vendors(website)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company_name ON vendors(company_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deployment_model ON vendors(deployment_model)')
    
    conn.commit()
    return conn

def load_vendor_data(industry):
    """Load vendor data from JSON files"""
    vendors = []
    pattern = f"vendor_logs/{industry}_*.json"
    
    for json_file in glob.glob(pattern):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'vendors' in data:
                    vendors.extend(data['vendors'])
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    return vendors

def insert_vendor(cursor, vendor):
    """Insert or update vendor in database"""
    # Convert lists to JSON strings
    for field in ['products', 'deployment_characteristics', 'technology_stack', 
                 'integration_capabilities', 'compliance_certifications']:
        if field in vendor and isinstance(vendor[field], list):
            vendor[field] = json.dumps(vendor[field])
    
    # Prepare fields and values
    fields = [k for k in vendor.keys() if k != 'id']
    placeholders = ','.join(['?' for _ in fields])
    values = [vendor.get(field, None) for field in fields]
    
    # Insert or update
    cursor.execute(f'''
    INSERT OR REPLACE INTO vendors ({','.join(fields)})
    VALUES ({placeholders})
    ''', values)

def process_industry(industry):
    """Process all vendor data for an industry"""
    print(f"\nProcessing {industry} industry...")
    
    # Setup database
    conn = setup_database(industry)
    cursor = conn.cursor()
    
    # Load vendor data
    vendors = load_vendor_data(industry)
    print(f"Found {len(vendors)} vendors in JSON files")
    
    # Insert vendors
    for vendor in vendors:
        try:
            insert_vendor(cursor, vendor)
        except Exception as e:
            print(f"Error inserting vendor {vendor.get('company_name', 'Unknown')}: {e}")
    
    # Commit changes
    conn.commit()
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cursor.fetchone()[0]
    print(f"Total vendors in database: {total_vendors}")
    
    # Close connection
    conn.close()

def main():
    """Main function to process all industries"""
    print("Starting database setup and data migration...")
    
    # Process each industry
    for industry in INDUSTRIES:
        process_industry(industry)
    
    print("\nDatabase setup and data migration completed!")

if __name__ == "__main__":
    main() 