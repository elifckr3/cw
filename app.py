import re

import dotenv
import pandas as pd
import requests
import time
import atexit
import glob

import os
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
from outlook_email import send_outlook_email
from title_categorizer import categorize_title
import logging

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
df = None

app.logger.setLevel(logging.INFO)

app.config['DF_FOLDER'] = 'dataframes'  # Define the key before using it

# Make sure the DataFrame folder exists
os.makedirs(app.config['DF_FOLDER'], exist_ok=True)


@app.route('/send-email', methods=['POST'])
def send_email_route():
    # Capture the form data
    recipient_email = request.form.get('recipient_email')
    subject = request.form.get('subject')
    body = request.form.get('body')

    # Call the send_outlook_email function with the form data
    send_outlook_email(recipient_email, subject, body)
    return "Email sent successfully!"


# Normalize the address
def normalize_address(address):
    if pd.isna(address):
        return ""
    address = str(address).lower()
    address = re.sub(r'\b(street)\b', 'st', address)
    address = re.sub(r'\b(road)\b', 'rd', address)
    address = re.sub(r'\b(avenue)\b', 'ave', address)
    # More substitutions as needed
    address = re.sub(r'[^\w\s]', '', address)
    address = re.sub(r'\s+', ' ', address).strip()
    return address


# without chatgpt
def are_addresses_similar(addr1, addr2):
    norm_addr1 = normalize_address(addr1)
    norm_addr2 = normalize_address(addr2)

    similarity_score = fuzz.ratio(norm_addr1, norm_addr2)
    return similarity_score > 90


def check_owner_occupancy(property_address, mailing_address):
    norm_property_address = normalize_address(property_address)
    norm_mailing_address = normalize_address(mailing_address)
    return norm_property_address == norm_mailing_address


@app.route('/process-contact-title', methods=['POST'])
def process_contact_title():
    selected_title = request.form['contact_title']

    return redirect(url_for('greeting'))


@app.route('/')
def index():
    return render_template('index.html', filename=None)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            # Read the uploaded file into a DataFrame
            df = pd.read_csv(file_path)

            # Check if the 'contact_title' column is in the DataFrame
            if 'contact_title' not in df.columns:
                return 'The uploaded file does not contain a "contact_title" column.'

            # Apply the categorization function to the contact_title column
            df['contact_category'] = df['contact_title'].apply(categorize_title)

            # Create a list of unique categories for the dropdown menu
            categories = ['VIEW ALL'] + sorted(df['contact_category'].astype(str).unique())

            # Save the DataFrame to a temporary file
            timestamp = int(time.time())
            temp_filename = f"df_{timestamp}.pkl"
            df.to_pickle(os.path.join(app.config['DF_FOLDER'], temp_filename))

            # Pass the categories, temp_filename, and filename back to the index template
            # The filename is added to the context so that it can be displayed after the page reloads
            return render_template('index.html', categories=categories, df_file=temp_filename, filename=filename)

        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        return 'Invalid file type'


@app.route('/filter_by_category', methods=['POST'])
def filter_by_category():
    df_path = request.form['df_path']
    selected_category = request.form['category']
    owner_occupier_selection = request.form.get('owner_occupier', 'all')

    full_df_path = os.path.join(app.config['DF_FOLDER'], df_path)

    if not os.path.isfile(full_df_path):
        return jsonify({"error": "The provided path is not a file."})

        # Load the DataFrame from the temporary file
    df = pd.read_pickle(full_df_path)

    # Replace 'nan' strings and NaN values with an empty string in the DataFrame
    df = df.fillna('').replace('nan', '')

    # If "VIEW ALL" is selected, assign the entire DataFrame to filtered_df
    if selected_category == 'VIEW ALL':
        filtered_df = df
        title = 'List of All Contacts'
    else:
        # Filter by the selected category
        filtered_df = df[df['contact_category'] == selected_category]

        # If the category is "Owner" or "Owner/Principal", further filter based on owner occupancy
        if selected_category in ['Owner', 'Owner/Principal']:
            if owner_occupier_selection == 'yes':
                filtered_df = filtered_df[filtered_df.apply(
                    lambda row: check_owner_occupancy(row['address_full'], row['reported_mailing_address_full']),
                    axis=1
                )]
                title = 'List of Owner-Occupiers'
            elif owner_occupier_selection == 'no':
                filtered_df = filtered_df[filtered_df.apply(
                    lambda row: not check_owner_occupancy(row['address_full'], row['reported_mailing_address_full']),
                    axis=1
                )]
                title = 'List of Owner Non-Occupiers'
            else:
                # If "all" is selected, no additional filtering is applied
                title = 'List of Owners'
        else:
            # For other categories, create a title based on the category name
            title = f'List of {selected_category}s' if not selected_category.endswith(
                's') else f'List of {selected_category}'

    # Convert the filtered DataFrame to a dictionary for the template
    properties = filtered_df.to_dict(orient='records')

    # Render the template with the filtered properties and the title
    return render_template('contact_table.html', properties=properties, title=title)

# dataframes fi

@app.route('/check-occupier', methods=['POST'])
def check_occupier():
    owner_occupier = request.form.get('owner_occupier') == 'yes'
    global df
    if df is not None and owner_occupier:
        owner_occupiers = []
        for _, row in df.iterrows():
            if are_addresses_similar(row['address_full'], row['reported_mailing_address_full']):
                owner_occupiers.append(row.to_dict())

        # Render the template with owner-occupiers
        # print("Owner Occupiers: ", owner_occupiers)
        return render_template('contact_table.html', properties=owner_occupiers)
    else:
        # Handle other cases or return a message
        return "No owner-occupier information available or DataFrame not loaded."


@app.route('/list-owner-principals')
def list_owner_principals():
    global df
    if df is not None:
        owner_principals_df = df[df['contact_title'] == 'Owner/Principal']
        properties = owner_principals_df.to_dict(orient='records')
        return render_template('contact_table.html', properties=properties)
    else:
        return "DataFrame is not loaded or file not uploaded."


@app.route('/create-email', methods=['POST'])
def create_email():
    # Retrieve address, name, and email from form data
    # Assuming 'address_line_1' is the form data for just the first line of the address
    address_line_1 = request.form.get('address_line_1')
    full_name = request.form.get('full_name')
    recipient_email = request.form.get('contact_email')

    # Split full_name to get the first name for a more personalized email greeting
    first_name = full_name.split()[0] if full_name else 'Valued Customer'

    # Define the subject of the email
    subject = f"Potential Offer for {address_line_1}"

    body = f"""
    {first_name}- 

    I am reaching out to you about your property at {address_line_1}. Based on my research, it appears that you are the owner. Would you be open to considering an unsolicited offer to purchase your property? If so, can I give you a 5-minute call just to see what is important to you so I can present an offer? 
    Thanks in advance.
    """

    # Render the email_template.html with the specific data for the contact
    return render_template('email_template.html',
                           recipient_email=recipient_email,
                           full_name=full_name,
                           full_address=address_line_1,  # Now using address_line_1 here
                           subject=subject,
                           body=body)



@app.route('/create-email-for-all', methods=['POST'])
def create_email_for_all():
    # ... logic to handle the incoming data ...

    # Instead of passing real recipient data, use placeholders
    placeholder_email = "Email"
    placeholder_content = (
        "\"Name\"- I am reaching out to you about your building at "
        "\"Address\". Would you be willing to look at an unsolicited offer to "
        "purchase your building? If so, can I give you a 5-minute call just to "
        "see what is important to you so I can present an offer? Thanks in advance."
    )
    placeholder_subject = "Potential Property Purchase Offer"

    return render_template(
        'email_template.html',
        recipient_email=placeholder_email,
        body=placeholder_content,
        subject=placeholder_subject
    )


# Define the cleanup function
def cleanup_temporary_dataframes():
    files = glob.glob('dataframes/*.pkl')
    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            print(f"Error deleting file {f}: {e.strerror}")

# Register the cleanup function to be called on app exit
atexit.register(cleanup_temporary_dataframes)

@app.route('/email')
def email_page():
    return "Email Page"


if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)


