import os
import json
import sqlite3
from tabulate import tabulate
from datetime import datetime

# Database configuration
DB_DIR = "databases"
INDUSTRIES = ["chiropractic", "optometry", "auto_repair"]

def connect_to_db(industry):
    """Connect to industry database"""
    db_path = os.path.join(DB_DIR, f"{industry}.db")
    if not os.path.exists(db_path):
        print(f"Database for {industry} not found!")
        return None
    return sqlite3.connect(db_path)

def get_vendor_stats(conn):
    """Get statistics about vendors in the database"""
    cursor = conn.cursor()
    
    # Total vendors
    cursor.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cursor.fetchone()[0]
    
    # Vendors by deployment model
    cursor.execute("""
    SELECT deployment_model, COUNT(*) as count
    FROM vendors
    GROUP BY deployment_model
    ORDER BY count DESC
    """)
    deployment_stats = cursor.fetchall()
    
    # Vendors by platform type
    cursor.execute("""
    SELECT platform_type, COUNT(*) as count
    FROM vendors
    GROUP BY platform_type
    ORDER BY count DESC
    """)
    platform_stats = cursor.fetchall()
    
    return {
        "total_vendors": total_vendors,
        "deployment_stats": deployment_stats,
        "platform_stats": platform_stats
    }

def get_top_vendors(conn, limit=5):
    """Get top vendors by confidence score"""
    cursor = conn.cursor()
    cursor.execute("""
    SELECT company_name, website, confidence_score, deployment_model, platform_type
    FROM vendors
    ORDER BY confidence_score DESC
    LIMIT ?
    """, (limit,))
    return cursor.fetchall()

def search_vendors(conn, query):
    """Search vendors by name or description"""
    cursor = conn.cursor()
    cursor.execute("""
    SELECT company_name, website, description, deployment_model, platform_type
    FROM vendors
    WHERE company_name LIKE ? OR description LIKE ?
    LIMIT 10
    """, (f"%{query}%", f"%{query}%"))
    return cursor.fetchall()

def main():
    """Main function to query and analyze vendor data"""
    print("Vendor Database Analysis")
    print("=" * 50)
    
    for industry in INDUSTRIES:
        print(f"\nAnalyzing {industry.upper()} industry:")
        print("-" * 50)
        
        conn = connect_to_db(industry)
        if not conn:
            continue
            
        # Get statistics
        stats = get_vendor_stats(conn)
        
        print(f"\nTotal Vendors: {stats['total_vendors']}")
        
        print("\nDeployment Model Distribution:")
        print(tabulate(stats['deployment_stats'], 
                      headers=['Deployment Model', 'Count'],
                      tablefmt='grid'))
        
        print("\nPlatform Type Distribution:")
        print(tabulate(stats['platform_stats'],
                      headers=['Platform Type', 'Count'],
                      tablefmt='grid'))
        
        print("\nTop 5 Vendors by Confidence Score:")
        top_vendors = get_top_vendors(conn)
        print(tabulate(top_vendors,
                      headers=['Company', 'Website', 'Confidence', 'Deployment', 'Platform'],
                      tablefmt='grid'))
        
        # Interactive search
        while True:
            query = input("\nEnter search term (or 'q' to quit): ").strip()
            if query.lower() == 'q':
                break
                
            results = search_vendors(conn, query)
            if results:
                print("\nSearch Results:")
                print(tabulate(results,
                             headers=['Company', 'Website', 'Description', 'Deployment', 'Platform'],
                             tablefmt='grid'))
            else:
                print("No results found.")
        
        conn.close()

if __name__ == "__main__":
    main() 