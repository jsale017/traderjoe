
import streamlit as st
import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus
import matplotlib.pyplot as plt
from google.colab import files as FILE
import os
import requests
import time
import streamlit as st

# Download TJ's logo
img_data = requests.get('https://cdn.worldvectorlogo.com/logos/trader-joes-logo.svg').content # https://1000logos.net/wp-content/uploads/2022/03/Trader-Joes-Logo.png
with open('logo.svg', 'wb') as handler:
    handler.write(img_data)

st.image('logo.svg')
st.title("Optimal Trader Joe's Grocery List")

st.write("Welcome to the Trader Joe's Grocery List Optimizer. Use the sidebar to set your preferences.")

st.sidebar.header("Set Your Preferences")

st.sidebar.subheader("Weekly Preferences")
# Budget input
Budget_Preference = st.sidebar.number_input("Enter your weekly budget ($)", min_value=0, value=150, step=5)
# Broad Preferences
Repetition_Preference = st.sidebar.number_input("Enter maximum quantity per item selected (weekly)", min_value=0, value=3, step=1)
Fruit_Preference = st.sidebar.number_input("Enter minimum types of fresh fruit included (weekly)", min_value=0, value=7, step=1)
Alternatives_Preference = st.sidebar.number_input("Enter number of item alternatives/substitutions requested", min_value=0, value=5, step=1)

# Macro Preferences
st.sidebar.subheader("Daily Macro Preferences")
Calorie_Preference = st.sidebar.number_input("Enter your daily calorie Preference", min_value=0, value=2200, step=100)
Protein_Preference = st.sidebar.number_input("Min. Protein (g)", min_value=0, value=60, step=5)
Carbohydrate_Preference = st.sidebar.number_input("Min. Carbohydrates (g)", min_value=0, value=250, step=10)
Fat_Preference = st.sidebar.number_input("Max. Fat (g)", min_value=0, value=80, step=5)

# Micro Preferences
st.sidebar.subheader("Daily Micro Preferences")
Sodium_Preference = st.sidebar.number_input("Max. Sodium (mg)", min_value=0, value=3000, step=100)
Fiber_Preference = st.sidebar.number_input("Min. Fiber (g)", min_value=0, value=20, step=1)
Sugar_Preference = st.sidebar.number_input("Max. Sugar (g)", min_value=0, value=60, step=1)
Cholesterol_Preference = st.sidebar.number_input("Max. Cholesterol (mg)", min_value=0, value=300, step=10)
Saturated_Fat_Preference = st.sidebar.number_input("Max. Saturated Fat (g)", min_value=0, value=25, step=1)
Vitamin_D_Preference = st.sidebar.number_input("Min. Vitamin D (mcg)", min_value=0, value=15, step=1)

preferences_dict = {'Calorie':Calorie_Preference, 'Protein':Protein_Preference, 'Fat':Fat_Preference, 'Carbohydrate':Carbohydrate_Preference, 'Sodium':Sodium_Preference,
                        'Fiber':Fiber_Preference,'Sugar':Sugar_Preference, 'Cholesterol':Cholesterol_Preference,'Saturated_Fat':Saturated_Fat_Preference,
                    'Vitamin_D':Vitamin_D_Preference, 'Repetition':Repetition_Preference, 'Fruit':Fruit_Preference, 'Alternatives':Alternatives_Preference}


# import TJs data

@st.cache_data
def load_df():
    return pd.read_csv('cleaned_data_latest.csv')

nutrition_data_cleaned = load_df()


def optimize_grocery_list(data=nutrition_data_cleaned, preferences_dict=preferences_dict):

    # creating  model
    uimodel = LpProblem("Optimal_Grocery_List", LpMinimize)
    x = {i: LpVariable(f"x_{i}", lowBound = 0, upBound=preferences_dict['Repetition'], cat="Integer") for i in nutrition_data_cleaned.index}
    # creating constraints

    # weekly values
    uimodel += lpSum(nutrition_data_cleaned.loc[i, 'retail_price'] * x[i] for i in nutrition_data_cleaned.index), "Total Cost"
    uimodel += lpSum(nutrition_data_cleaned.loc[i, 'retail_price'] * x[i] for i in nutrition_data_cleaned.index) <= Budget_Preference, "Budget_Constraint"
    uimodel += lpSum(nutrition_data_cleaned.loc[i, 'fresh'] * x[i] for i in nutrition_data_cleaned.index) >= Fruit_Preference, "Fruit_Constraint"



    column_dict = {'Calorie':'calories', 'Protein':'protein', 'Fat':'total_fat', 'Carbohydrate':'total_carbohydrates', 'Sodium':'sodium','Fiber':'dietary_fiber','Sugar':'sugars',
                          'Cholesterol':'cholesterol','Saturated_Fat':'saturated_fat','Vitamin_D':'vitamin_d', 'Fruit':'fresh'}

    for item in list(column_dict.keys()):
        if item in ['Fat', 'Sodium', 'Sugar', 'Cholesterol', 'Saturated_Fat']: # max
          uimodel += lpSum(nutrition_data_cleaned.loc[i, column_dict[item]] * x[i] for i in nutrition_data_cleaned.index) <= preferences_dict[item]*7, f"{item}_Constraint"
        if item in ['Calorie',  'Protein',  'Carbohydrate',  'Fiber',  'Vitamin_D']: # min
          uimodel += lpSum(nutrition_data_cleaned.loc[i, column_dict[item]] * x[i] for i in nutrition_data_cleaned.index) >= preferences_dict[item]*7, f"{item}_Constraint"    # solving on click

    # Run Model
    uimodel.solve()
    print("Model Status:", LpStatus[uimodel.status])
    optimal_items_dict = {nutrition_data_cleaned.loc[i, 'item']: x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1}
    optimal_items = list(optimal_items_dict.keys())
    optimal_qty = list(optimal_items_dict.values())
    optimal_items_with_qty = [optimal_items[i] + ' x ' + str(optimal_qty[i]) for i in range(len(optimal_items))]
    # Macros
    Calories = sum(nutrition_data_cleaned.loc[i, 'calories'] * x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1)
    Protein = sum(nutrition_data_cleaned.loc[i, 'protein'] * x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1)
    Fat = sum(nutrition_data_cleaned.loc[i, 'total_fat'] * x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1)
    Carbohydrates = sum(nutrition_data_cleaned.loc[i, 'total_carbohydrates'] * x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1)
    macros = [Calories, Protein,Fat,Carbohydrates]
    total_cost = sum(nutrition_data_cleaned.loc[i, 'retail_price'] * x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1)

    # Generate Alternatives
    K = preferences_dict['Alternatives'] # fetch top K solutions
    iter = 0
    removed_items = []
    added_items = []
    while True:
        try: # delete existing constraint if exists
          del uimodel.constraints['OptimalSol']
        except:
          pass
        uimodel += lpSum(nutrition_data_cleaned.loc[i, 'retail_price'] * x[i] for i in nutrition_data_cleaned.index) >= total_cost+iter+1.0, f"OptimalSol"
        uimodel.solve()
        # The solution is printed if it was deemed "optimal" i.e met the constraints
        if LpStatus[uimodel.status] == "Optimal":
            selected_items_dict = {nutrition_data_cleaned.loc[i, 'item']: x[i].value() for i in nutrition_data_cleaned.index if x[i].value() >= 1}
            selected_items = list(selected_items_dict.keys())
            selected_qty = list(selected_items_dict.values())
            selected_items_with_qty = [selected_items[i] + ' x ' + str(selected_qty[i]) for i in range(len(selected_items))]

            removed_items.append(list(set(optimal_items) - set(selected_items)))
            added_items.append(list(set(selected_items) - set(optimal_items)))

            iter +=1
            if iter >= K: # only get top K
              try: # delete existing constraint if exists
                del uimodel.constraints['OptimalSol']
              except:
                pass
              break
        # If a new optimal solution cannot be found, we end the program
        else:
            break
    alternatives_df = pd.DataFrame({'Remove these items':removed_items,'Add these items':added_items})

    return optimal_items_dict, macros, total_cost, alternatives_df

# Displaying Results

if st.button("Optimize Grocery List"):

    selected_items_dict, macros, total_cost, alternatives_df =  optimize_grocery_list()
    with st.status("Generating Optimal Grocery List", expanded=True):
      st.write("Defining Model...")
      time.sleep(2)
      st.write("Solving Model...")
      time.sleep(3)
      st.write("Generating Alternatives...")
      time.sleep(5)

    st.success("Optimization complete!")
    st.subheader("Optimal Grocery List")

    selected_items = list(selected_items_dict.keys())
    selected_qty = list(selected_items_dict.values())
    selected_items_df = pd.DataFrame({'Item':selected_items, 'Qty':selected_qty})

    matching_rows = nutrition_data_cleaned[nutrition_data_cleaned['item'].isin(selected_items)]
    try:

      # retrieve item w/ features from dataframe
      display_rows = matching_rows.drop(columns=['iron', 'calcium', 'potassium', 'fresh'], )
      display_rows = display_rows.rename(columns={'serving_size':'Serving Size'	, 'calories':'Calories',	'total_fat':'Total Fat',	'saturated_fat':"Saturated Fat",	'trans_fat':'Trans Fat',
                      'cholesterol':'Cholesterol',	'sodium':'Sodium',	'total_carbohydrates':'Carbs',	'dietary_fiber':'Fiber',	'sugars':'Sugar',
                      "protein":'Protein',	'vitamin_d':"Vitamin D", 'item':'Item', 'retail_price':'Price'})
      display_rows = display_rows.merge(selected_items_df, how='left', on='Item')
      col_order = ['Item', 'Qty' ,'Price', 'Serving Size', 'Calories', 'Carbs','Protein', 'Total Fat', 'Saturated Fat', 'Cholesterol',
                'Sodium',  'Fiber', 'Sugar', 'Vitamin D', ]
      display_rows = display_rows[col_order]
      st.dataframe(display_rows)
    except:
      st.dataframe(matching_rows)


    st.subheader(f"Total Cost: ${total_cost:.2f} | Total Calories - {macros[0]:.0f}")
    st.subheader(f"MACROS: Protein - {macros[1]:.0f} | Fat - {macros[2]:.0f} | Carbs - {macros[3]:.0f}")

    st.subheader("Substitutions")
    st.write("""Swap these items from the generated list with any set of alternative to create a meal plan more suited to your taste.
    Alternatives are nearly identical in Macros, and only $1-4 more expensive than the original list.""")
    st.dataframe(alternatives_df)


    # Visualize the results
    st.subheader("Macronutrient Distribution")
    nutrient_data = pd.DataFrame({
        'Nutrient': ['Protein', 'Fat', 'Carbohydrates'],
        'Amount': [macros[1], macros[2], macros[3]]
    })

    # Pie chart, Macros:
    macronutrient_data = pd.DataFrame({
            'Nutrient': ['Protein', 'Fat', 'Carbohydrates'],
            'Amount': [macros[1], macros[2], macros[3]]
        })

    explode = (0.1, 0, 0.1)  # only "explode" the protein and carb slices

    fig1, ax1 = plt.subplots()
    ax1.pie(macronutrient_data['Amount'].to_list(), explode=explode, labels=macronutrient_data['Nutrient'].to_list(),
            shadow=True, startangle=90, autopct='%1.1f%%')
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    st.pyplot(fig1)

    st.subheader("Micronutrient Distribution (mg)")

    # Pie chart, Micros:
    micronutrient_data = pd.DataFrame({
            'Nutrient':['Cholesterol','Sodium','Vitamin D', "Calcium",'Iron','Potassium'],
            'Amount':  matching_rows[['cholesterol','sodium','vitamin_d','calcium','iron','potassium']].sum().values
        })

    explode = (0.1, 0.1, 0 ,0,0,0)  # only "explode" the chol and sodium slices

    fig2, ax2 = plt.subplots()
    ax2.pie(micronutrient_data['Amount'].to_list(), labels=micronutrient_data['Nutrient'].to_list(),
            shadow=True, startangle=90, autopct='%d')
    ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    st.pyplot(fig2)

