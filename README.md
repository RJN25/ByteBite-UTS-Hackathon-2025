# ByteBite-UTS-Hackathon-2025

## _Co-created by Arjan Waraich and Daniel Ganjali_

## Project Overview
ByteBite is an inventory management system designed to help food banks manage their stock efficiently. The system includes user authentication, inventory tracking, and integration with the Nutritionix API to fetch nutritional information. This was 

## Features

  ### User Authentication:
    - Sign Up: Users can create an account with a username, email, and password.
    - Sign In: Users can log in using their email or username and password.
    - JWT-based authentication for secure access to protected routes.
    - Logout functionality to clear user session.
  
  ### Inventory Management:
    - Add new stock items with details such as food type, quantity, and expiration date.
    - Fetch nutritional information for food items using the Nutritionix API.
    - View current stock with details including nutritional information.
    - Delete stock items from the inventory.

  ### Nutritionix API Integration:
    - Search for food items and fetch nutritional information.
    - Debounced search to optimize API calls.
    
  ### Frontend - Web Design:
    - Responsive design with a clean and user-friendly interface.
    - Separate pages for sign-in, sign-up, and dashboard, run on JSON and MongoDB
    - Autocomplete functionality for food type input.

  ### Backend - Random Forest Regression (RFR) Machine Learning Model:
    -  Leverages Sci-kitlearn and Pandas for data preprocessing
    -  Utilizes vector standardization and normalization across 9 curcial, distinct input feautures involving:
         -      'food_item',
                'food_type',
                'current_quantity',
                'expiration_date',
                'days_until_expiry',
                'calories',
                'sugars',
                'nutritional_ratio',
                'weekly_customers'
    - Employs bagging data technique, performs randomized regression, and aggregates common agreed result to provide each Item a Ranking Score
    - Yields an effective triage-based systems about sequence and priority of distributing a distinct food item, to optimize the logistical nightmare, prevent spoilage, and feed families reliably!
