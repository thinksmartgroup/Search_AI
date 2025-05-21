import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import logging
import glob

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'vendor_ml_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class VendorML:
    def __init__(self):
        self.models = {}
        self.vectorizers = {}
        self.scalers = {}
        self.data = {}
        
    def load_data(self):
        """Load data from Google Sheets and logs"""
        logging.info("Loading data from sheets and logs...")
        
        # Load credentials
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Load environment variables
        load_dotenv()
        
        # Get sheet URLs
        sheet_urls = {
            "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
            "chiropractic": os.getenv("CHIRO_SHEET_URL"),
            "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
        }
        
        # Load data from sheets
        for industry, url in sheet_urls.items():
            if not url:
                continue
                
            try:
                sheet = client.open_by_url(url).sheet1
                data = sheet.get_all_values()
                
                if len(data) <= 1:
                    continue
                    
                # Convert to DataFrame
                df = pd.DataFrame(data[1:], columns=data[0])
                self.data[industry] = df
                logging.info(f"Loaded {len(df)} vendors from {industry} sheet")
                
            except Exception as e:
                logging.error(f"Error loading {industry} sheet: {str(e)}")
                
        # Load data from logs
        log_data = self._load_log_data()
        if log_data:
            self.data['logs'] = log_data
            
    def _load_log_data(self):
        """Load and process data from log files"""
        log_files = glob.glob('logs/*.log')
        if not log_files:
            return None
            
        log_data = []
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    
                # Extract vendor data using regex
                vendor_data = self._extract_vendor_data(content)
                if vendor_data:
                    log_data.extend(vendor_data)
                    
            except Exception as e:
                logging.error(f"Error processing log file {log_file}: {str(e)}")
                
        return pd.DataFrame(log_data) if log_data else None
        
    def _extract_vendor_data(self, content):
        """Extract vendor data from log content"""
        vendors = []
        # Add regex patterns to extract vendor data
        # This is a simplified version - you might want to add more patterns
        vendor_pattern = r'vendor_data:\s*({[^}]+})'
        matches = re.finditer(vendor_pattern, content)
        
        for match in matches:
            try:
                vendor_json = match.group(1)
                vendor_data = json.loads(vendor_json)
                vendors.append(vendor_data)
            except:
                continue
                
        return vendors
        
    def preprocess_data(self):
        """Preprocess data for ML models"""
        logging.info("Preprocessing data...")
        
        for industry, df in self.data.items():
            # Handle text data
            if 'products' in df.columns:
                # Create TF-IDF vectorizer for products
                self.vectorizers[f'{industry}_products'] = TfidfVectorizer(
                    max_features=1000,
                    stop_words='english'
                )
                product_features = self.vectorizers[f'{industry}_products'].fit_transform(
                    df['products'].fillna('')
                )
                
            # Handle numerical data
            numerical_cols = ['company_size', 'founding_year']
            if any(col in df.columns for col in numerical_cols):
                # Scale numerical features
                self.scalers[industry] = StandardScaler()
                numerical_data = df[numerical_cols].fillna(0)
                scaled_data = self.scalers[industry].fit_transform(numerical_data)
                
            # Store preprocessed data
            self.data[f'{industry}_processed'] = {
                'product_features': product_features if 'products' in df.columns else None,
                'numerical_features': scaled_data if any(col in df.columns for col in numerical_cols) else None
            }
            
    def train_models(self):
        """Train ML models on the data"""
        logging.info("Training models...")
        
        for industry, processed_data in self.data.items():
            if not industry.endswith('_processed'):
                continue
                
            industry_name = industry.replace('_processed', '')
            
            # Train clustering model
            if processed_data['product_features'] is not None:
                # Use PCA to reduce dimensionality
                pca = PCA(n_components=50)
                reduced_features = pca.fit_transform(processed_data['product_features'].toarray())
                
                # Train K-means clustering
                kmeans = KMeans(n_clusters=5, random_state=42)
                clusters = kmeans.fit_predict(reduced_features)
                
                self.models[f'{industry_name}_clusters'] = {
                    'pca': pca,
                    'kmeans': kmeans,
                    'clusters': clusters
                }
                
            # Train classification model if we have target variables
            if 'pricing_model' in self.data[industry_name].columns:
                X = processed_data['numerical_features']
                y = self.data[industry_name]['pricing_model']
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
                
                # Train Random Forest
                rf = RandomForestClassifier(n_estimators=100, random_state=42)
                rf.fit(X_train, y_train)
                
                # Store model and metrics
                self.models[f'{industry_name}_classifier'] = {
                    'model': rf,
                    'accuracy': rf.score(X_test, y_test)
                }
                
    def save_models(self):
        """Save trained models to disk"""
        logging.info("Saving models...")
        
        # Create models directory if it doesn't exist
        os.makedirs('models', exist_ok=True)
        
        # Save models
        for name, model in self.models.items():
            joblib.dump(model, f'models/{name}.joblib')
            
        # Save vectorizers
        for name, vectorizer in self.vectorizers.items():
            joblib.dump(vectorizer, f'models/{name}_vectorizer.joblib')
            
        # Save scalers
        for name, scaler in self.scalers.items():
            joblib.dump(scaler, f'models/{name}_scaler.joblib')
            
    def analyze_results(self):
        """Analyze and display model results"""
        logging.info("Analyzing results...")
        
        for industry, processed_data in self.data.items():
            if not industry.endswith('_processed'):
                continue
                
            industry_name = industry.replace('_processed', '')
            
            # Analyze clusters
            if f'{industry_name}_clusters' in self.models:
                clusters = self.models[f'{industry_name}_clusters']
                logging.info(f"\nCluster Analysis for {industry_name}:")
                logging.info(f"Number of clusters: {len(np.unique(clusters['clusters']))}")
                
                # Get top terms for each cluster
                if processed_data['product_features'] is not None:
                    feature_names = self.vectorizers[f'{industry_name}_products'].get_feature_names_out()
                    for i in range(len(np.unique(clusters['clusters']))):
                        cluster_terms = feature_names[clusters['pca'].components_[i].argsort()[-10:]]
                        logging.info(f"Cluster {i} top terms: {', '.join(cluster_terms)}")
                        
            # Analyze classifier
            if f'{industry_name}_classifier' in self.models:
                classifier = self.models[f'{industry_name}_classifier']
                logging.info(f"\nClassifier Analysis for {industry_name}:")
                logging.info(f"Accuracy: {classifier['accuracy']:.2f}")
                
    def run(self):
        """Run the complete ML pipeline"""
        try:
            self.load_data()
            self.preprocess_data()
            self.train_models()
            self.save_models()
            self.analyze_results()
            logging.info("ML pipeline completed successfully!")
            
        except Exception as e:
            logging.error(f"Error in ML pipeline: {str(e)}")

if __name__ == "__main__":
    ml = VendorML()
    ml.run() 