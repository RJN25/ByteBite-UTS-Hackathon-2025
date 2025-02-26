import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import GradientBoostingRegressor
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')
from flask import Flask, request, jsonify

app = Flask(__name__)

class FoodBankDatabase:
    def __init__(self, user_id):
        # start the database
        self.user_id = user_id
        self.excel_path = f'backend-model/user_data/inventory_{user_id}.xlsx'
        self.ensure_user_directory()
        
    def ensure_user_directory(self):
        directory = 'backend-model/user_data'
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        if not os.path.exists(self.excel_path):
            # excel columns (case-sensitive!!)
            df = pd.DataFrame(columns=[
                'food_item',
                'food_type',
                'current_quantity',
                'expiration_date',
                'days_until_expiry',
                'calories',
                'sugars',
                'nutritional_ratio',
                'weekly_customers'
            ])
            # save empty data frane
            df.to_excel(self.excel_path, index=False)
            print(f"Created new inventory file for user {self.user_id}")
    
    def add_inventory_item(self, item_data):
        """Add new inventory item to user's Excel file."""
        try:
            self.ensure_user_directory()
            
            try:
                df = pd.read_excel(self.excel_path)
            except:
                df = pd.DataFrame(columns=[
                    'food_item',
                    'food_type',
                    'current_quantity',
                    'expiration_date',
                    'days_until_expiry',
                    'calories',
                    'sugars',
                    'nutritional_ratio',
                    'weekly_customers'
                ])
            
            # Calculate days until expiry
            expiry_date = pd.to_datetime(item_data['expiration_date'])
            days_until_expiry = (expiry_date - pd.Timestamp.now()).days

            new_row = {
                'food_item': item_data['type'],
                'food_type': item_data['category'],
                'current_quantity': item_data['quantity'],
                'expiration_date': expiry_date,
                'days_until_expiry': days_until_expiry,
                'calories': item_data['nutritional_value']['calories'],
                'sugars': item_data['nutritional_value']['sugars'],
                'nutritional_ratio': item_data['nutritional_value']['calories'] / (item_data['nutritional_value']['sugars'] + 1),
                'weekly_customers': 100
            }
            
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.excel_path), exist_ok=True)
            
            # Save with openpyxl engine
            df.to_excel(self.excel_path, index=False, engine='openpyxl')
            print(f"Successfully added item to inventory for user {self.user_id}")
            return True
        except Exception as e:
            print(f"Error adding inventory item: {str(e)}")
            return False

    def load_data(self):
        try:
            if not os.path.exists(self.excel_path):
                return pd.DataFrame()
            
            df = pd.read_excel(self.excel_path)
            if df.empty:
                return df
                
            # Convert expiration_date to datetime if it's not already
            df['expiration_date'] = pd.to_datetime(df['expiration_date'])
            
            # Recalculate days_until_expiry
            df['days_until_expiry'] = (df['expiration_date'] - pd.Timestamp.now()).dt.days
            
            # Ensure all numeric columns are properly typed
            numeric_columns = ['current_quantity', 'calories', 'sugars', 'weekly_customers']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Replace any NaN values with appropriate defaults
            df['weekly_customers'] = df['weekly_customers'].fillna(100)
            df['nutritional_ratio'] = df['calories'] / (df['sugars'] + 1)
            
            return df
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return pd.DataFrame()

class FoodBankDistributionModel:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        # Switch to GradientBoostingRegressor for better predictions
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42
        )
    
    def preprocess_data(self, df):
        if df.empty:
            return pd.DataFrame()
        
        processed_df = df.copy()
        
        # Handle categorical columns
        categorical_columns = ['food_type', 'food_item']
        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
            # Handle new categories that weren't in training
            unique_values = processed_df[col].unique()
            if hasattr(self.label_encoders[col], 'classes_'):
                new_values = set(unique_values) - set(self.label_encoders[col].classes_)
                if new_values:
                    self.label_encoders[col].classes_ = np.concatenate([
                        self.label_encoders[col].classes_,
                        np.array(list(new_values))
                    ])
            processed_df[col] = self.label_encoders[col].fit_transform(processed_df[col])
        
        feature_columns = [
            'days_until_expiry',
            'food_type',
            'current_quantity',
            'nutritional_ratio',
            'weekly_customers',
            'calories',
            'sugars'
        ]
        
        X = processed_df[feature_columns]
        
        # Scale features
        X = pd.DataFrame(self.scaler.fit_transform(X), columns=X.columns)
        
        return X
    
    def calculate_priority_scores(self, df):
        if df.empty:
            return np.array([])
            
        scores = np.zeros(len(df))
        
        # Normalize values to 0-1 range for each component
        expiry_score = 1 / (df['days_until_expiry'].clip(1) + 1)
        nutritional_score = (df['nutritional_ratio'] - df['nutritional_ratio'].min()) / \
                          (df['nutritional_ratio'].max() - df['nutritional_ratio'].min() + 1e-6)
        quantity_score = df['current_quantity'] / df['weekly_customers']
        
        # Weighted sum of components
        scores = (
            expiry_score * 0.4 +           # 40% weight for expiration
            nutritional_score * 0.25 +     # 25% weight for nutrition
            quantity_score * 0.35          # 35% weight for quantity/demand ratio
        )
        
        # Normalize final scores to 0-1 range
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-6)
        
        return scores
    
    def calculate_recommended_quantities(self, df):
        if df.empty:
            return np.array([])
            
        # Base calculation on weekly customers and current quantity
        base = df['weekly_customers'] * 0.1  # Start with 10% of weekly customers
        
        # Adjust based on days until expiry (distribute more if closer to expiry)
        expiry_factor = 1 + (1 / (df['days_until_expiry'].clip(1) + 1))
        
        # Adjust based on nutritional value
        nutrition_factor = 1 + (df['nutritional_ratio'] / df['nutritional_ratio'].max())
        
        # Calculate final quantities
        quantities = base * expiry_factor * nutrition_factor
        
        # Ensure we don't recommend more than current quantity
        quantities = quantities.clip(1, df['current_quantity'])
        
        return quantities.round()
    
    def train(self, df):
        if df.empty:
            return
            
        X = self.preprocess_data(df)
        y_priority = self.calculate_priority_scores(df)
        y_quantity = self.calculate_recommended_quantities(df)
        
        # Train model on both targets
        self.model.fit(X, np.column_stack((y_priority, y_quantity)))
    
    def predict(self, df):
        if df.empty:
            return {'priority_scores': [], 'recommended_quantities': []}
            
        X = self.preprocess_data(df)
        predictions = self.model.predict(X)
        
        # Ensure predictions are within valid ranges
        priority_scores = predictions[:, 0].clip(0, 1)
        recommended_quantities = predictions[:, 1].clip(1, df['current_quantity'].max())
        
        return {
            'priority_scores': priority_scores,
            'recommended_quantities': recommended_quantities.round()
        }
    
    def get_distribution_plan(self, df):
        if df.empty:
            return df
            
        predictions = self.predict(df)
        
        results = df.copy()
        results['priority_score'] = predictions['priority_scores']
        results['recommended_quantity'] = predictions['recommended_quantities']
        
        # Sort by priority score descending and take top 10
        results = results.sort_values('priority_score', ascending=False).head(10)
        results['rank'] = range(1, len(results) + 1)
        
        # Save the top 10 distribution plan with timestamp
        if hasattr(self, 'user_id'):
            # Use consistent naming pattern for distribution plan file
            output_path = f'backend-model/user_data/distribution_plan_{self.user_id}.xlsx'
            results['last_updated'] = pd.Timestamp.now()
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            results.to_excel(output_path, index=False, engine='openpyxl')
            print(f"Updated distribution plan for user {self.user_id}")
        
        return results

@app.route('/predict', methods=['POST'])

def predict():
    try:
        data = request.json
        user_id = data.get('user_id')
        
        # initialize db
        db = FoodBankDatabase(user_id)
        
        # load any inventory data
        df = db.load_data()
        
        if df.empty:
            return jsonify({
                'success': True,
                'distribution_plan': []
            })
        
        #  now predict
        model = FoodBankDistributionModel()
        model.train(df)
        distribution_plan = model.get_distribution_plan(df)
        
        response = {
            'success': True,
            'distribution_plan': distribution_plan[['food_item', 'food_type', 
                'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                'priority_score', 'rank']].to_dict('records')
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# sample usage for the 1000 row foodbank_dataset.xlsx training file (simulate inventory data)

def main():
    
    user_id = input("Enter user ID: ")
    db = FoodBankDatabase(user_id)
               
    try:
        # load again
        data = db.load_data()
        
        # gauge the size of the spreadsheet
        num_rows = data.shape[0]
        
        print()
        print(f"There are {num_rows} entries in the food inventory spreadsheet.")
        print()
        try:
            num_ranks = int(input("Enter the number of entries that you want to be ranked for optimized distribution: "))
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
            return
        
        # run the training model
        model = FoodBankDistributionModel()
        model.train(data)
        
        # output a new excel, disribution_plan.xlsx
        distribution_plan = model.get_distribution_plan(data)
        
        # display
        print(f"\nTop {num_ranks} Priority Items:")
        print(distribution_plan[['food_item', 'food_type', 'days_until_expiry', 
                               'current_quantity', 'recommended_quantity', 
                               'priority_score', 'rank']].head(num_ranks))
        
        # save!
        distribution_plan.to_excel("distribution_plan.xlsx", index=False)
        print("\nFull distribution plan saved to 'distribution_plan.xlsx'")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
    
if __name__ == "__main__":
    app.run(debug=True)
