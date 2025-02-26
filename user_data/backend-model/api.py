#!/usr/bin/env python3
import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np
# Add openpyxl import
import openpyxl
from foodbank_regression import FoodBankDatabase, FoodBankDistributionModel
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, 
     resources={
         r"/*": {  # Changed from r"/api/*" to r"/*"
             "origins": ["http://localhost:5001", "http://localhost:5002", "https://blueshacksByteBite.onrender.com"],
             "methods": ["GET", "POST", "OPTIONS", "DELETE"],  # Added OPTIONS
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True
         }
     })

model = FoodBankDistributionModel()

# Add health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

def handle_add_item(data):
    """Handle adding new item to user's inventory."""
    try:
        user_id = data['user_id']
        item_data = data['item_data']
        
        db = FoodBankDatabase(user_id)
        success = db.add_inventory_item(item_data)
        
        return {'success': success}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/api/inventory', methods=['GET', 'OPTIONS'])
def get_inventory():
    if request.method == 'OPTIONS':
        return '', 200
    # ... rest of your inventory code

@app.route('/api/search', methods=['GET', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        return '', 200
    # ... rest of your search code

@app.route('/api/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        user_id = data.get('user_id')
        
        # Initialize database
        db = FoodBankDatabase(user_id)
        df = db.load_data()
        
        if df.empty:
            return jsonify({
                'success': True,
                'distribution_plan': []
            })
            
        # Get predictions
        model = FoodBankDistributionModel()
        model.train(df)
        distribution_plan = model.get_distribution_plan(df)
        
        # Get top 10 items by priority score
        top_10_plan = distribution_plan.nlargest(10, 'priority_score')
        
        response = {
            'success': True,
            'distribution_plan': top_10_plan[['food_item', 'food_type', 
                'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                'priority_score', 'rank']].to_dict('records')
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in prediction: {str(e)}", file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'add_item':
            data = json.loads(sys.argv[2])
            result = handle_add_item(data)
            print(json.dumps(result))
            sys.exit(0 if result['success'] else 1)
        elif command == 'predict':
            data = json.loads(sys.argv[2])
            user_id = data['user_id']
            db = FoodBankDatabase(user_id)
            df = db.load_data()
            
            if df.empty:
                print(json.dumps({
                    'success': True,
                    'distribution_plan': []
                }))
                sys.exit(0)
            
            # Get predictions
            try:
                model.train(df)
                distribution_plan = model.get_distribution_plan(df)
                
                # Use consistent file path
                distribution_file = f'backend-model/user_data/distribution_plan_{user_id}.xlsx'
                distribution_plan.to_excel(distribution_file, index=False, engine='openpyxl')
                
                # Read back top 10 items
                saved_plan = pd.read_excel(distribution_file)
                top_10_plan = saved_plan.nlargest(10, 'priority_score')
                
                response = {
                    'success': True,
                    'distribution_plan': top_10_plan[['food_item', 'food_type', 
                        'days_until_expiry', 'current_quantity', 'recommended_quantity', 
                        'priority_score', 'rank']].to_dict('records')
                }
                
                print(json.dumps(response))
                sys.exit(0)
            except ValueError as ve:
                print(json.dumps({
                    'success': False,
                    'error': str(ve)
                }))
                sys.exit(1)
    else:
        # Get port from environment variable for Render
        port = int(os.environ.get('PORT', 5002))
        # Allow any host to connect and enable debug mode
        app.run(host='0.0.0.0', port=port, debug=True)
